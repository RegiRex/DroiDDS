//! CodexAstraUlt: Original fixtures compare the optimized query against an
//! independent enumeration of blocked waits and registered timer objects.

use super::*;

// CodexAstraUlt: Enumerate from blocked waiters rather than following the
// production timer-candidate loop. Registration remains part of the contract.
fn enumerated_deadline(kernel: &Kernel) -> Option<u64> {
    kernel.threads.iter().filter(|thread| thread.status.is_blocked()).flat_map(|thread| {
        thread.wakeup_at.into_iter().chain(thread.wait_objects.iter().filter_map(|id| {
            if !kernel.timers.contains(id) {
                return None;
            }
            match kernel.objects.get(*id) {
                Some(KObject::Timer(timer)) => timer.fire_at,
                _ => None,
            }
        }))
    }).min()
}

fn timer(kernel: &mut Kernel, at: Option<u64>, registered: bool) -> ObjectId {
    let object = kernel.objects.insert(KObject::Timer(sync::Timer {
        name: "original-deadline".into(), reset_type: ResetType::OneShot,
        signaled: false, fire_at: at, interval: 0,
    }));
    if registered {
        kernel.timers.push(object);
    }
    object
}

fn waiter(kernel: &mut Kernel, status: ThreadStatus, at: Option<u64>, objects: Vec<ObjectId>) -> ThreadId {
    let id = kernel.create_thread("original-waiter", 0x0010_0000, 0x1000_0000, 0, 0x30, 0);
    let thread = kernel.thread_mut(id);
    thread.status = status;
    thread.wakeup_at = at;
    thread.wait_objects = objects;
    id
}

#[test]
fn deadline_filters_unarmed_unwaited_unregistered_and_stale_candidates() {
    let mut kernel = Kernel::new(0, MemoryRegion::Application, 0x1400_0000);
    let unwaited = timer(&mut kernel, Some(0), true);
    let unarmed = timer(&mut kernel, None, true);
    let registered = timer(&mut kernel, Some(90), true);
    let unregistered = timer(&mut kernel, Some(1), false);
    let ordinary = kernel.objects.insert(KObject::Event(sync::Event::new(ResetType::OneShot, "original-event")));
    let stale = ObjectId(u32::MAX);
    kernel.timers.extend([ordinary, stale, registered]);
    let thread = waiter(&mut kernel, ThreadStatus::WaitSync, Some(100),
        vec![unarmed, registered, unregistered, ordinary, stale]);
    assert_eq!(kernel.next_event(), Some(90));
    assert_eq!(kernel.next_event(), enumerated_deadline(&kernel));
    kernel.thread_mut(thread).wait_objects.push(unwaited);
    assert_eq!(kernel.next_event(), Some(0));
    kernel.thread_mut(thread).status = ThreadStatus::Ready;
    assert_eq!(kernel.next_event(), None);
}

#[test]
fn deadline_query_observes_mutations_without_cross_step_cache() {
    let mut kernel = Kernel::new(0, MemoryRegion::Application, 0x1400_0000);
    let object = timer(&mut kernel, Some(50), true);
    let thread = waiter(&mut kernel, ThreadStatus::WaitSync, Some(80), vec![object]);
    assert_eq!(kernel.next_event(), Some(50));
    let Some(KObject::Timer(timer)) = kernel.objects.get_mut(object) else { unreachable!() };
    timer.fire_at = None;
    assert_eq!(kernel.next_event(), Some(80));
    kernel.thread_mut(thread).wakeup_at = Some(10);
    assert_eq!(kernel.next_event(), Some(10));
    kernel.thread_mut(thread).wakeup_at = None;
    assert_eq!(kernel.next_event(), None);
    let Some(KObject::Timer(timer)) = kernel.objects.get_mut(object) else { unreachable!() };
    timer.fire_at = Some(u64::MAX);
    assert_eq!(kernel.next_event(), Some(u64::MAX));
    kernel.timers.clear();
    assert_eq!(kernel.next_event(), None);
}

#[test]
fn unobserved_minimum_and_ties_still_find_the_first_waited_deadline() {
    // CodexAstraUlt: The prepass must fall through when the first armed minimum
    // has no waiter, including when a different waited timer has the same tick.
    let mut kernel = Kernel::new(0, MemoryRegion::Application, 0x1400_0000);
    let unwaited = timer(&mut kernel, Some(10), true);
    let waited = timer(&mut kernel, Some(10), true);
    let later = timer(&mut kernel, Some(20), true);
    let id = waiter(&mut kernel, ThreadStatus::WaitSync, None, vec![waited, later]);
    assert_eq!(kernel.next_event(), Some(10));
    kernel.thread_mut(id).wait_objects = vec![later];
    assert_eq!(kernel.next_event(), Some(20));
    kernel.timers.reverse();
    assert_eq!(kernel.next_event(), Some(20));
    kernel.thread_mut(id).wait_objects.push(unwaited);
    assert_eq!(kernel.next_event(), Some(10));
}

#[test]
fn all_thread_states_and_deadline_orders_match_independent_enumeration() {
    // CodexAstraUlt: A fixed generated corpus covers ties, no deadlines, stale
    // references, registered/nonregistered timers, and changing registration
    // order. It uses no random dependency or game-derived state.
    let states = [ThreadStatus::Running, ThreadStatus::Ready, ThreadStatus::Sleeping,
        ThreadStatus::WaitSync, ThreadStatus::WaitArbiter, ThreadStatus::Dormant, ThreadStatus::Dead];
    let mut seed = 0xC0DE_A57Au32;
    let mut next = || {
        seed = seed.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
        seed
    };
    for _ in 0..256 {
        let mut kernel = Kernel::new(0, MemoryRegion::Application, 0x1400_0000);
        let mut objects = Vec::new();
        for _ in 0..16 {
            let value = next();
            objects.push(timer(&mut kernel, (value % 5 != 0).then_some(u64::from(value % 13)), value % 3 != 0));
        }
        objects.push(ObjectId(u32::MAX));
        for status in states {
            let value = next();
            let waits = (0..(value % 6)).map(|_| objects[next() as usize % objects.len()]).collect();
            waiter(&mut kernel, status, (value % 4 != 0).then_some(u64::from(value % 17)), waits);
        }
        let expected = enumerated_deadline(&kernel);
        assert_eq!(kernel.next_event(), expected);
        kernel.timers.reverse();
        assert_eq!(kernel.next_event(), expected);
        if !kernel.timers.is_empty() {
            kernel.timers.rotate_left(1);
        }
        assert_eq!(kernel.next_event(), expected);
    }
}
