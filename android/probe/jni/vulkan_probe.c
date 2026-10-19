/* CodexAstraUlt: Preserve the original Vulkan 1.0 offscreen baseline and add
 * a separately reported Vulkan 1.3 renderer capability/pipeline fixture. These
 * synthetic paths do not establish PICA accuracy, game speed or leak freedom. */
#include "vulkan_probe.h"
#include "vulkan_renderer.h"
#include "droidds_probe_shaders.h"

#include <inttypes.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vulkan/vulkan.h>

/* CodexAstraUlt: The optional host gate must load the actual Khronos layer and
 * fail if absent. Android always uses the device's ordinary Vulkan loader. */
#ifndef DROIDDS_VK_VALIDATION
#define DROIDDS_VK_VALIDATION 0
#endif
#if DROIDDS_VK_VALIDATION && defined(__ANDROID__)
#error "DROIDDS_VK_VALIDATION is a host-only validation build option"
#endif

enum { WIDTH = 16, HEIGHT = 16, PIXELS = 256, BYTES = 1024,
       CYCLES = 3, CASES = 3, MAX_DEVICES = 16, MAX_QUEUES = 64 };
static const VkDeviceSize ALLOCATION_LIMIT = 16 * 1024 * 1024;
static const char *const CASE_NAMES[CASES] = {
    "solid_red", "solid_green", "split_red_green"
};

/* CodexAstraUlt: Fixed-size host records and allocation caps prevent unbounded
 * enumeration or diagnostic growth. Only non-unique GPU properties are exposed. */
typedef struct {
    uint32_t cycles, pixels, mismatches;
} CaseResult;

typedef struct {
    const char *status;
    const char *error_step;
    VkResult error_result;
    uint32_t cycles, pipelines, draws, negative_checks;
    int negative_ok, has_device, validation_layer_enabled;
    VkPhysicalDeviceProperties properties;
    CaseResult cases[CASES];
    /* CodexAstraUlt: Separate bounded renderer evidence preserves baseline counters. */
    char renderer_json[16384];
} Report;

typedef struct {
    VkDevice device;
    VkQueue queue;
    VkImage image;
    VkDeviceMemory image_memory;
    VkImageView view;
    VkBuffer buffer;
    VkDeviceMemory buffer_memory;
    void *mapped;
    int coherent, submitted;
    VkRenderPass render_pass;
    VkFramebuffer framebuffer;
    VkShaderModule vertex, fragment;
    VkPipelineLayout layout;
    VkPipeline pipeline;
    VkCommandPool pool;
    VkCommandBuffer command;
    VkFence fence;
} Cycle;

static int fail(Report *report, const char *step, VkResult result) {
    report->error_step = step;
    report->error_result = result;
    return 0;
}

/* CodexAstraUlt: Propagate every fallible Vulkan result with its actual call
 * site. Cleanup runs after this function returns even during partial creation. */
#define VK_REQUIRE(report, call) do { \
    VkResult result_ = (call); \
    if (result_ != VK_SUCCESS) return fail((report), #call, result_); \
} while (0)

static int memory_type(const VkPhysicalDeviceMemoryProperties *properties,
                       uint32_t allowed, VkMemoryPropertyFlags required,
                       VkMemoryPropertyFlags preferred, uint32_t *index) {
    for (int pass = 0; pass < 2; ++pass) {
        VkMemoryPropertyFlags flags = required | (pass == 0 ? preferred : 0);
        for (uint32_t i = 0; i < properties->memoryTypeCount; ++i) {
            if ((allowed & (1u << i)) != 0 &&
                (properties->memoryTypes[i].propertyFlags & flags) == flags) {
                *index = i;
                return 1;
            }
        }
    }
    return 0;
}

/* CodexAstraUlt: Selection requires an actual graphics queue and the exact
 * attachment/copy usage. Enumeration overflow is an explicit unsupported probe
 * environment, never a truncated list presented as complete coverage. */
static int select_device(VkInstance instance, Report *report,
                         VkPhysicalDevice *physical, uint32_t *queue_family) {
    uint32_t count = 0;
    VK_REQUIRE(report, vkEnumeratePhysicalDevices(instance, &count, NULL));
    if (count == 0 || count > MAX_DEVICES)
        return fail(report, "physical_device_count_bound", VK_ERROR_INITIALIZATION_FAILED);
    VkPhysicalDevice devices[MAX_DEVICES];
    VK_REQUIRE(report, vkEnumeratePhysicalDevices(instance, &count, devices));
    for (uint32_t i = 0; i < count; ++i) {
        VkImageFormatProperties image_properties;
        VkResult result = vkGetPhysicalDeviceImageFormatProperties(
            devices[i], VK_FORMAT_R8G8B8A8_UNORM, VK_IMAGE_TYPE_2D,
            VK_IMAGE_TILING_OPTIMAL,
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
            0, &image_properties);
        if (result == VK_ERROR_FORMAT_NOT_SUPPORTED) continue;
        if (result != VK_SUCCESS)
            return fail(report, "vkGetPhysicalDeviceImageFormatProperties", result);
        if (image_properties.maxExtent.width < WIDTH ||
            image_properties.maxExtent.height < HEIGHT ||
            (image_properties.sampleCounts & VK_SAMPLE_COUNT_1_BIT) == 0) continue;
        uint32_t queue_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &queue_count, NULL);
        if (queue_count == 0 || queue_count > MAX_QUEUES) continue;
        VkQueueFamilyProperties queues[MAX_QUEUES];
        vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &queue_count, queues);
        for (uint32_t q = 0; q < queue_count; ++q) {
            if (queues[q].queueCount != 0 &&
                (queues[q].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0) {
                *physical = devices[i];
                *queue_family = q;
                vkGetPhysicalDeviceProperties(devices[i], &report->properties);
                report->has_device = 1;
                return 1;
            }
        }
    }
    return fail(report, "select_graphics_device", VK_ERROR_FEATURE_NOT_PRESENT);
}

/* CodexAstraUlt: Each cycle owns a new device, image, readback allocation and
 * pipeline. Host-visible memory is invalidated when it is not coherent. */
static int create_resources(Cycle *cycle, Report *report,
                            VkPhysicalDevice physical, uint32_t queue_family) {
    float priority = 1.0f;
    VkDeviceQueueCreateInfo queue_info = {
        .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        .queueFamilyIndex = queue_family, .queueCount = 1, .pQueuePriorities = &priority
    };
    VkDeviceCreateInfo device_info = {
        .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        .queueCreateInfoCount = 1, .pQueueCreateInfos = &queue_info
    };
    VK_REQUIRE(report, vkCreateDevice(physical, &device_info, NULL, &cycle->device));
    vkGetDeviceQueue(cycle->device, queue_family, 0, &cycle->queue);
    VkPhysicalDeviceMemoryProperties memory;
    vkGetPhysicalDeviceMemoryProperties(physical, &memory);

    VkImageCreateInfo image_info = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType = VK_IMAGE_TYPE_2D, .format = VK_FORMAT_R8G8B8A8_UNORM,
        .extent = { WIDTH, HEIGHT, 1 }, .mipLevels = 1, .arrayLayers = 1,
        .samples = VK_SAMPLE_COUNT_1_BIT, .tiling = VK_IMAGE_TILING_OPTIMAL,
        .usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE, .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED
    };
    VK_REQUIRE(report, vkCreateImage(cycle->device, &image_info, NULL, &cycle->image));
    VkMemoryRequirements requirements;
    vkGetImageMemoryRequirements(cycle->device, cycle->image, &requirements);
    uint32_t type = 0;
    if (requirements.size == 0 || requirements.size > ALLOCATION_LIMIT)
        return fail(report, "image_allocation_bound", VK_ERROR_OUT_OF_DEVICE_MEMORY);
    if (!memory_type(&memory, requirements.memoryTypeBits, 0,
                     VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, &type))
        return fail(report, "image_memory_type", VK_ERROR_FEATURE_NOT_PRESENT);
    VkMemoryAllocateInfo allocation = {
        .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        .allocationSize = requirements.size, .memoryTypeIndex = type
    };
    VK_REQUIRE(report, vkAllocateMemory(cycle->device, &allocation, NULL, &cycle->image_memory));
    VK_REQUIRE(report, vkBindImageMemory(cycle->device, cycle->image, cycle->image_memory, 0));
    VkImageViewCreateInfo view_info = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image = cycle->image, .viewType = VK_IMAGE_VIEW_TYPE_2D,
        .format = VK_FORMAT_R8G8B8A8_UNORM,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 }
    };
    VK_REQUIRE(report, vkCreateImageView(cycle->device, &view_info, NULL, &cycle->view));
    VkBufferCreateInfo buffer_info = {
        .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = BYTES,
        .usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT, .sharingMode = VK_SHARING_MODE_EXCLUSIVE
    };
    VK_REQUIRE(report, vkCreateBuffer(cycle->device, &buffer_info, NULL, &cycle->buffer));
    vkGetBufferMemoryRequirements(cycle->device, cycle->buffer, &requirements);
    if (requirements.size < BYTES || requirements.size > ALLOCATION_LIMIT)
        return fail(report, "readback_allocation_bound", VK_ERROR_OUT_OF_DEVICE_MEMORY);
    if (!memory_type(&memory, requirements.memoryTypeBits,
                     VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT,
                     VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, &type))
        return fail(report, "host_visible_memory_type", VK_ERROR_FEATURE_NOT_PRESENT);
    cycle->coherent = (memory.memoryTypes[type].propertyFlags &
                       VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) != 0;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = type;
    VK_REQUIRE(report, vkAllocateMemory(cycle->device, &allocation, NULL, &cycle->buffer_memory));
    VK_REQUIRE(report, vkBindBufferMemory(cycle->device, cycle->buffer, cycle->buffer_memory, 0));
    VK_REQUIRE(report, vkMapMemory(cycle->device, cycle->buffer_memory, 0,
                                  VK_WHOLE_SIZE, 0, &cycle->mapped));

    VkAttachmentDescription attachment = {
        .format = VK_FORMAT_R8G8B8A8_UNORM, .samples = VK_SAMPLE_COUNT_1_BIT,
        .loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR, .storeOp = VK_ATTACHMENT_STORE_OP_STORE,
        .stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE,
        .stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
        .finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL
    };
    VkAttachmentReference color = { 0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL };
    VkSubpassDescription subpass = {
        .pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS,
        .colorAttachmentCount = 1, .pColorAttachments = &color
    };
    VkSubpassDependency dependencies[2] = {
        { .srcSubpass = VK_SUBPASS_EXTERNAL, .dstSubpass = 0,
          .srcStageMask = VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
          .dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
          .dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT },
        { .srcSubpass = 0, .dstSubpass = VK_SUBPASS_EXTERNAL,
          .srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
          .dstStageMask = VK_PIPELINE_STAGE_TRANSFER_BIT,
          .srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
          .dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT }
    };
    VkRenderPassCreateInfo pass_info = {
        .sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
        .attachmentCount = 1, .pAttachments = &attachment,
        .subpassCount = 1, .pSubpasses = &subpass,
        .dependencyCount = 2, .pDependencies = dependencies
    };
    VK_REQUIRE(report, vkCreateRenderPass(cycle->device, &pass_info, NULL, &cycle->render_pass));
    VkFramebufferCreateInfo framebuffer_info = {
        .sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
        .renderPass = cycle->render_pass, .attachmentCount = 1, .pAttachments = &cycle->view,
        .width = WIDTH, .height = HEIGHT, .layers = 1
    };
    VK_REQUIRE(report, vkCreateFramebuffer(cycle->device, &framebuffer_info, NULL,
                                          &cycle->framebuffer));
    return 1;
}

/* CodexAstraUlt: Exactly one graphics pipeline is created per device cycle.
 * Color changes are push constants and the split uses dynamic scissor state. */
static int create_pipeline(Cycle *cycle, Report *report, uint32_t queue_family) {
    VkShaderModuleCreateInfo shader = {
        .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
        .codeSize = sizeof(droidds_probe_vert_spv), .pCode = droidds_probe_vert_spv
    };
    VK_REQUIRE(report, vkCreateShaderModule(cycle->device, &shader, NULL, &cycle->vertex));
    shader.codeSize = sizeof(droidds_probe_frag_spv);
    shader.pCode = droidds_probe_frag_spv;
    VK_REQUIRE(report, vkCreateShaderModule(cycle->device, &shader, NULL, &cycle->fragment));
    VkPushConstantRange push = { VK_SHADER_STAGE_FRAGMENT_BIT, 0, 4 * sizeof(float) };
    VkPipelineLayoutCreateInfo layout = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .pushConstantRangeCount = 1, .pPushConstantRanges = &push
    };
    VK_REQUIRE(report, vkCreatePipelineLayout(cycle->device, &layout, NULL, &cycle->layout));
    VkPipelineShaderStageCreateInfo stages[2] = {
        { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
          .stage = VK_SHADER_STAGE_VERTEX_BIT, .module = cycle->vertex, .pName = "main" },
        { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
          .stage = VK_SHADER_STAGE_FRAGMENT_BIT, .module = cycle->fragment, .pName = "main" }
    };
    VkPipelineVertexInputStateCreateInfo vertex = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO
    };
    VkPipelineInputAssemblyStateCreateInfo assembly = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
        .topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST
    };
    VkViewport viewport = { 0, 0, WIDTH, HEIGHT, 0, 1 };
    VkRect2D scissor = { {0, 0}, {WIDTH, HEIGHT} };
    VkPipelineViewportStateCreateInfo viewport_state = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
        .viewportCount = 1, .pViewports = &viewport, .scissorCount = 1, .pScissors = &scissor
    };
    VkPipelineRasterizationStateCreateInfo raster = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
        .polygonMode = VK_POLYGON_MODE_FILL, .cullMode = VK_CULL_MODE_NONE,
        .frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE, .lineWidth = 1.0f
    };
    VkPipelineMultisampleStateCreateInfo multisample = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
        .rasterizationSamples = VK_SAMPLE_COUNT_1_BIT
    };
    VkPipelineColorBlendAttachmentState blend_attachment = {
        .colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                          VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT
    };
    VkPipelineColorBlendStateCreateInfo blend = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
        .attachmentCount = 1, .pAttachments = &blend_attachment
    };
    VkDynamicState dynamic_scissor = VK_DYNAMIC_STATE_SCISSOR;
    VkPipelineDynamicStateCreateInfo dynamic = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
        .dynamicStateCount = 1, .pDynamicStates = &dynamic_scissor
    };
    VkGraphicsPipelineCreateInfo pipeline = {
        .sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
        .stageCount = 2, .pStages = stages, .pVertexInputState = &vertex,
        .pInputAssemblyState = &assembly, .pViewportState = &viewport_state,
        .pRasterizationState = &raster, .pMultisampleState = &multisample,
        .pColorBlendState = &blend, .pDynamicState = &dynamic,
        .layout = cycle->layout, .renderPass = cycle->render_pass, .subpass = 0,
        .basePipelineIndex = -1
    };
    VK_REQUIRE(report, vkCreateGraphicsPipelines(cycle->device, VK_NULL_HANDLE,
                                                1, &pipeline, NULL, &cycle->pipeline));
    ++report->pipelines;
    VkCommandPoolCreateInfo pool = {
        .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
        .queueFamilyIndex = queue_family
    };
    VK_REQUIRE(report, vkCreateCommandPool(cycle->device, &pool, NULL, &cycle->pool));
    VkCommandBufferAllocateInfo command = {
        .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool = cycle->pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
        .commandBufferCount = 1
    };
    VK_REQUIRE(report, vkAllocateCommandBuffers(cycle->device, &command, &cycle->command));
    VkFenceCreateInfo fence = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    VK_REQUIRE(report, vkCreateFence(cycle->device, &fence, NULL, &cycle->fence));
    return 1;
}

/* CodexAstraUlt: Expected colors are independently computed for every pixel and
 * every channel, including alpha. One bad channel makes that pixel a mismatch. */
static uint32_t compare_pixels(const uint8_t *pixels, uint32_t pattern) {
    uint32_t mismatches = 0;
    for (uint32_t y = 0; y < HEIGHT; ++y) {
        for (uint32_t x = 0; x < WIDTH; ++x) {
            int green = pattern == 1 || (pattern == 2 && x >= WIDTH / 2);
            const uint8_t expected[4] = { green ? 0 : 255, green ? 255 : 0, 0, 255 };
            if (memcmp(pixels + (y * WIDTH + x) * 4, expected, 4) != 0) ++mismatches;
        }
    }
    return mismatches;
}

static void draw_color(Cycle *cycle, uint32_t x, uint32_t width, int green) {
    const float color[4] = { green ? 0.0f : 1.0f, green ? 1.0f : 0.0f, 0.0f, 1.0f };
    VkRect2D scissor = { { (int32_t)x, 0 }, { width, HEIGHT } };
    vkCmdSetScissor(cycle->command, 0, 1, &scissor);
    vkCmdPushConstants(cycle->command, cycle->layout, VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(color), color);
    vkCmdDraw(cycle->command, 3, 1, 0, 0);
}

/* CodexAstraUlt: Explicit render/copy/host dependencies and fence completion
 * precede readback. The copy has tightly packed rows, independent of image pitch. */
static int render_case(Cycle *cycle, Report *report, uint32_t pattern) {
    VK_REQUIRE(report, vkResetFences(cycle->device, 1, &cycle->fence));
    VK_REQUIRE(report, vkResetCommandBuffer(cycle->command, 0));
    VkCommandBufferBeginInfo begin = {
        .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
    };
    VK_REQUIRE(report, vkBeginCommandBuffer(cycle->command, &begin));
    VkClearValue clear = { .color = { .float32 = { 0, 0, 0, 0 } } };
    VkRenderPassBeginInfo pass = {
        .sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
        .renderPass = cycle->render_pass, .framebuffer = cycle->framebuffer,
        .renderArea = { {0, 0}, {WIDTH, HEIGHT} }, .clearValueCount = 1, .pClearValues = &clear
    };
    vkCmdBeginRenderPass(cycle->command, &pass, VK_SUBPASS_CONTENTS_INLINE);
    vkCmdBindPipeline(cycle->command, VK_PIPELINE_BIND_POINT_GRAPHICS, cycle->pipeline);
    if (pattern == 2) {
        draw_color(cycle, 0, WIDTH / 2, 0);
        draw_color(cycle, WIDTH / 2, WIDTH / 2, 1);
    } else {
        draw_color(cycle, 0, WIDTH, pattern == 1);
    }
    vkCmdEndRenderPass(cycle->command);
    VkBufferImageCopy region = {
        .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
        .imageExtent = { WIDTH, HEIGHT, 1 }
    };
    vkCmdCopyImageToBuffer(cycle->command, cycle->image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                           cycle->buffer, 1, &region);
    VkBufferMemoryBarrier host = {
        .sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
        .srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT, .dstAccessMask = VK_ACCESS_HOST_READ_BIT,
        .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .buffer = cycle->buffer, .offset = 0, .size = VK_WHOLE_SIZE
    };
    vkCmdPipelineBarrier(cycle->command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                          VK_PIPELINE_STAGE_HOST_BIT, 0, 0, NULL, 1, &host, 0, NULL);
    VK_REQUIRE(report, vkEndCommandBuffer(cycle->command));
    VkSubmitInfo submit = {
        .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
        .commandBufferCount = 1, .pCommandBuffers = &cycle->command
    };
    /* CodexAstraUlt: An unsuccessful submission is conservatively treated as
     * possibly active until idle/loss is established during cleanup. */
    cycle->submitted = 1;
    VK_REQUIRE(report, vkQueueSubmit(cycle->queue, 1, &submit, cycle->fence));
    VK_REQUIRE(report, vkWaitForFences(cycle->device, 1, &cycle->fence, VK_TRUE, UINT64_MAX));
    cycle->submitted = 0;
    report->draws += pattern == 2 ? 2 : 1;
    if (!cycle->coherent) {
        VkMappedMemoryRange range = {
            .sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
            .memory = cycle->buffer_memory, .offset = 0, .size = VK_WHOLE_SIZE
        };
        VK_REQUIRE(report, vkInvalidateMappedMemoryRanges(cycle->device, 1, &range));
    }
    uint8_t readback[BYTES];
    memcpy(readback, cycle->mapped, sizeof(readback));
    uint32_t mismatches = compare_pixels(readback, pattern);
    CaseResult *result = &report->cases[pattern];
    result->pixels += PIXELS;
    result->mismatches += mismatches;
    ++result->cycles;
    if (mismatches != 0)
        return fail(report, CASE_NAMES[pattern], VK_ERROR_UNKNOWN);

    /* CodexAstraUlt: Mutate the actual readback snapshot rather than a fabricated
     * expected image. Keeping mutation off mapped memory avoids dirty host cache
     * lines racing the next GPU copy on non-coherent memory. */
    readback[0] ^= 1;
    int rejected = compare_pixels(readback, pattern) == 1;
    readback[0] ^= 1;
    ++report->negative_checks;
    report->negative_ok = report->negative_ok && rejected;
    if (!rejected || compare_pixels(readback, pattern) != 0)
        return fail(report, "pixel_mutation_negative_control", VK_ERROR_UNKNOWN);
    return 1;
}

/* CodexAstraUlt: A failed fence wait cannot authorize destruction of in-flight
 * objects. Wait for device idle before error teardown; a driver hang here must
 * be handled by the external process supervisor, not unsafe early destruction. */
static void destroy_cycle(Cycle *cycle) {
    if (cycle->device == VK_NULL_HANDLE) return;
    if (cycle->submitted) {
        VkResult idle = vkDeviceWaitIdle(cycle->device);
        /* CodexAstraUlt: Unexpected idle errors cannot prove submitted work has
         * stopped. Fail the process rather than free live GPU resources or leak
         * a device into subsequent runs. The persisted running marker/external
         * runner makes this an incomplete failure, never a passing JSON result. */
        if (idle != VK_SUCCESS && idle != VK_ERROR_DEVICE_LOST) abort();
    }
    if (cycle->mapped) vkUnmapMemory(cycle->device, cycle->buffer_memory);
    if (cycle->fence) vkDestroyFence(cycle->device, cycle->fence, NULL);
    if (cycle->pool) vkDestroyCommandPool(cycle->device, cycle->pool, NULL);
    if (cycle->pipeline) vkDestroyPipeline(cycle->device, cycle->pipeline, NULL);
    if (cycle->layout) vkDestroyPipelineLayout(cycle->device, cycle->layout, NULL);
    if (cycle->fragment) vkDestroyShaderModule(cycle->device, cycle->fragment, NULL);
    if (cycle->vertex) vkDestroyShaderModule(cycle->device, cycle->vertex, NULL);
    if (cycle->framebuffer) vkDestroyFramebuffer(cycle->device, cycle->framebuffer, NULL);
    if (cycle->render_pass) vkDestroyRenderPass(cycle->device, cycle->render_pass, NULL);
    if (cycle->view) vkDestroyImageView(cycle->device, cycle->view, NULL);
    if (cycle->image) vkDestroyImage(cycle->device, cycle->image, NULL);
    if (cycle->image_memory) vkFreeMemory(cycle->device, cycle->image_memory, NULL);
    if (cycle->buffer) vkDestroyBuffer(cycle->device, cycle->buffer, NULL);
    if (cycle->buffer_memory) vkFreeMemory(cycle->device, cycle->buffer_memory, NULL);
    vkDestroyDevice(cycle->device, NULL);
}

/* CodexAstraUlt: Bounded JSON output escapes GPU names and call descriptions.
 * Capacity exhaustion returns an error and exposes no partially valid report. */
typedef struct { char *data; size_t capacity, used; int failed; } Writer;

static void append(Writer *writer, const char *format, ...)
    __attribute__((format(printf, 2, 3)));

static void append(Writer *writer, const char *format, ...) {
    if (writer->failed) return;
    va_list args;
    va_start(args, format);
    int count = vsnprintf(writer->data + writer->used,
                          writer->capacity - writer->used, format, args);
    va_end(args);
    if (count < 0 || (size_t)count >= writer->capacity - writer->used) {
        writer->failed = 1;
        return;
    }
    writer->used += (size_t)count;
}

static void quoted(Writer *writer, const char *text, size_t limit) {
    append(writer, "\"");
    for (size_t i = 0; i < limit && text[i] != '\0'; ++i) {
        unsigned char byte = (unsigned char)text[i];
        if (byte == '\\' || byte == '"') append(writer, "\\%c", byte);
        else if (byte < 0x20) append(writer, "\\u%04x", byte);
        else append(writer, "%c", byte);
    }
    append(writer, "\"");
}

static int serialize(const Report *report, char *json, size_t capacity) {
    Writer writer = { json, capacity, 0, 0 };
    append(&writer, "{\"schema\":2,\"kind\":\"droidds-vulkan-probe\",\"status\":");
    quoted(&writer, report->status, 32);
    append(&writer, ",\"validation_layer_enabled\":%s", report->validation_layer_enabled ? "true" : "false");
    append(&writer, ",\"width\":16,\"height\":16,\"required_cycles\":3,"
           "\"cycles_completed\":%" PRIu32 ",\"pipeline_creation_count\":%" PRIu32
           ",\"draw_count\":%" PRIu32 ",\"device\":", report->cycles,
           report->pipelines, report->draws);
    if (report->has_device) {
        const VkPhysicalDeviceProperties *device = &report->properties;
        append(&writer, "{\"name\":");
        quoted(&writer, device->deviceName, VK_MAX_PHYSICAL_DEVICE_NAME_SIZE);
        append(&writer, ",\"type\":%u,\"api_version\":%" PRIu32
               ",\"driver_version\":%" PRIu32 ",\"vendor_id\":%" PRIu32
               ",\"device_id\":%" PRIu32 "}", (unsigned)device->deviceType,
               device->apiVersion, device->driverVersion, device->vendorID, device->deviceID);
    } else append(&writer, "null");
    append(&writer, ",\"error\":");
    if (report->error_step) {
        append(&writer, "{\"step\":");
        quoted(&writer, report->error_step, 512);
        append(&writer, ",\"vk_result\":%d}", (int)report->error_result);
    } else append(&writer, "null");
    append(&writer, ",\"cases\":[");
    for (uint32_t i = 0; i < CASES; ++i) {
        const CaseResult *result = &report->cases[i];
        const char *status = result->mismatches ? "failed" :
            (result->cycles == CYCLES ? "passed" : "incomplete");
        append(&writer, "%s{\"name\":\"%s\",\"status\":\"%s\","
               "\"cycles_completed\":%" PRIu32 ",\"pixels_checked\":%" PRIu32
               ",\"mismatched_pixels\":%" PRIu32 "}", i ? "," : "", CASE_NAMES[i],
               status, result->cycles, result->pixels, result->mismatches);
    }
    append(&writer, "],\"negative_controls\":{\"pixel_mutation_rejected\":%s,"
           "\"checks_completed\":%" PRIu32 ",\"required_checks\":9}",
           report->negative_ok && report->negative_checks == CYCLES * CASES ? "true" : "false",
           report->negative_checks);
    append(&writer, ",\"renderer_probe\":%s}", report->renderer_json[0] ?
           report->renderer_json : "{\"schema\":1,\"status\":\"not_run\"}");
    if (writer.failed || writer.used > INT32_MAX) {
        json[0] = '\0';
        return -1;
    }
    return (int)writer.used;
}

/* CodexAstraUlt: Availability failure and executed correctness failure stay
 * distinct. Passing requires all nine baseline readbacks/mutation controls plus
 * the separately reported required capabilities and representative pipeline. */
int dds_vk_probe_run(char *json, size_t capacity) {
    if (!json || capacity == 0) return -1;
    Report report = { .status = "unavailable", .negative_ok = 1 };
    /* CodexAstraUlt: Negotiate up to 1.3 while retaining a 1.0 baseline on older
     * loaders. Resolve the version query dynamically for Android loader safety. */
    uint32_t instance_api = VK_API_VERSION_1_0;
    PFN_vkEnumerateInstanceVersion version = (PFN_vkEnumerateInstanceVersion)
        vkGetInstanceProcAddr(VK_NULL_HANDLE, "vkEnumerateInstanceVersion");
    if (version && version(&instance_api) != VK_SUCCESS) instance_api = VK_API_VERSION_1_0;
    if (instance_api > VK_API_VERSION_1_3) instance_api = VK_API_VERSION_1_3;
    VkApplicationInfo application = {
        .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .pApplicationName = "DroidDS Vulkan Probe",
        .applicationVersion = VK_MAKE_VERSION(0, 0, 4), .pEngineName = "DroidDS synthetic",
        .engineVersion = VK_MAKE_VERSION(0, 0, 4), .apiVersion = instance_api
    };
    VkInstanceCreateInfo instance_info = {
        .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &application
    };
#if DROIDDS_VK_VALIDATION
    const char *validation_layer = "VK_LAYER_KHRONOS_validation";
    instance_info.enabledLayerCount = 1;
    instance_info.ppEnabledLayerNames = &validation_layer;
#endif
    VkInstance instance = VK_NULL_HANDLE;
    VkResult result = vkCreateInstance(&instance_info, NULL, &instance);
    if (result != VK_SUCCESS) {
        fail(&report, "vkCreateInstance", result);
        return serialize(&report, json, capacity);
    }
    report.validation_layer_enabled = DROIDDS_VK_VALIDATION ? 1 : 0;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    uint32_t queue_family = 0;
    if (select_device(instance, &report, &physical, &queue_family)) {
        report.status = "failed";
        for (uint32_t i = 0; i < CYCLES; ++i) {
            Cycle cycle = {0};
            int ok = create_resources(&cycle, &report, physical, queue_family) &&
                     create_pipeline(&cycle, &report, queue_family);
            for (uint32_t pattern = 0; ok && pattern < CASES; ++pattern)
                ok = render_case(&cycle, &report, pattern);
            destroy_cycle(&cycle);
            if (!ok) break;
            ++report.cycles;
        }
        if (report.cycles == CYCLES && report.negative_checks == CYCLES * CASES &&
            report.negative_ok && !report.error_step) {
            int renderer_passed = 0;
            int length = dds_renderer_probe_run(instance, physical, instance_api,
                report.renderer_json, sizeof(report.renderer_json), &renderer_passed);
            if (length < 0) fail(&report, "renderer_serialization_bound", VK_ERROR_UNKNOWN);
            else if (!renderer_passed) fail(&report, "renderer_probe_not_passed", VK_ERROR_FEATURE_NOT_PRESENT);
            else report.status = "passed";
        }
    }
    vkDestroyInstance(instance, NULL);
    return serialize(&report, json, capacity);
}
