/* CodexAstraUlt: Original representative Vulkan probe, based on an independently
 * enumerated capability contract of Zakuro 412900a hardware.rs. This is not
 * copied renderer code or proof of PICA/game correctness. All data are synthetic. */
#include "vulkan_renderer.h"
#include "droidds_probe_shaders.h"
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { R_WIDTH = 16, R_HEIGHT = 16, R_PIXELS = 256, R_BYTES = 1024,
       R_WORDS = 16, R_MAX_EXTENSIONS = 512, R_MAX_QUEUES = 64, R_REQUIRED = 10 };
static const VkDeviceSize R_ALLOCATION_LIMIT = 16 * 1024 * 1024;
static const char *const R_NAMES[R_REQUIRED] = {
    "vulkan_1_3", "graphics_compute_queue", "push_descriptor", "depth_clamp",
    "d24s8_attachment", "rgba8_color_sample_transfer", "dynamic_rendering",
    "synchronization2", "pipeline_creation_cache_control", "push_descriptor_limit"
};

/* CodexAstraUlt: Fixed bounds apply to driver enumeration, host evidence, and
 * each GPU allocation. Optional capabilities never become silent prerequisites. */
typedef struct {
    const char *status, *error;
    VkResult result;
    uint32_t instance_api, physical_api, queue_family, max_push;
    int required[R_REQUIRED], optional[4];
    uint32_t pipelines, draws, dispatches, readbacks, pixels, mismatches;
    uint32_t words, word_mismatches, negatives;
    uint32_t case_pixels[2], case_mismatches[2], case_draws[2];
    int negative_ok;
} RReport;
typedef struct { VkImage image; VkDeviceMemory memory; VkImageView view; } RImage;
typedef struct {
    VkBuffer buffer; VkDeviceMemory memory; void *mapped; int coherent;
} RBuffer;
typedef struct {
    VkDevice device; VkQueue queue; VkPhysicalDeviceMemoryProperties memory;
    RImage color, depth, texture;
    RBuffer readback, upload, uniform, compute_result;
    VkSampler sampler;
    VkDescriptorSetLayout sets[2]; VkPipelineLayout layouts[2];
    VkShaderModule shaders[3]; VkPipeline pipelines[2];
    VkCommandPool pool; VkCommandBuffer command; VkFence fence; int submitted;
    PFN_vkCmdBeginRendering begin_rendering;
    PFN_vkCmdEndRendering end_rendering;
    PFN_vkCmdPipelineBarrier2 barrier;
    PFN_vkCmdSetStencilOp stencil_op;
    PFN_vkCmdPushDescriptorSetKHR push;
    PFN_vkQueueSubmit2 submit;
} RResources;
static int r_fail(RReport *report, const char *step, VkResult result) {
    report->error = step; report->result = result; report->status = "failed";
    return 0;
}
#define R_REQUIRE(report, call) do { VkResult r_ = (call); \
    if (r_ != VK_SUCCESS) return r_fail((report), #call, r_); } while (0)

/* CodexAstraUlt: Query the actual full image usages, rather than inferring a
 * renderer format from an attachment-only bit. D24S8 also supports transfers;
 * RGBA8 supports color, sampled, storage and transfer usages used by Zakuro. */
static int r_format(VkPhysicalDevice physical, VkFormat format,
                    VkImageUsageFlags usage, VkFormatFeatureFlags flags) {
    VkFormatProperties properties;
    vkGetPhysicalDeviceFormatProperties(physical, format, &properties);
    if ((properties.optimalTilingFeatures & flags) != flags) return 0;
    VkImageFormatProperties image;
    VkResult result = vkGetPhysicalDeviceImageFormatProperties(physical, format,
        VK_IMAGE_TYPE_2D, VK_IMAGE_TILING_OPTIMAL, usage, 0, &image);
    return result == VK_SUCCESS && image.maxExtent.width >= R_WIDTH &&
        image.maxExtent.height >= R_HEIGHT &&
        (image.sampleCounts & VK_SAMPLE_COUNT_1_BIT) != 0;
}
static int r_has_extension(const VkExtensionProperties *extensions, uint32_t count,
                           const char *name) {
    for (uint32_t i = 0; i < count; ++i)
        if (strncmp(extensions[i].extensionName, name, VK_MAX_EXTENSION_NAME_SIZE) == 0)
            return 1;
    return 0;
}
static int r_capabilities(VkInstance instance, VkPhysicalDevice physical,
                          RReport *report) {
    VkPhysicalDeviceProperties properties;
    VkPhysicalDeviceFeatures base;
    vkGetPhysicalDeviceProperties(physical, &properties);
    vkGetPhysicalDeviceFeatures(physical, &base);
    report->physical_api = properties.apiVersion;
    report->required[0] = report->instance_api >= VK_API_VERSION_1_3 &&
        properties.apiVersion >= VK_API_VERSION_1_3 &&
        VK_API_VERSION_VARIANT(properties.apiVersion) == 0;
    report->required[3] = base.depthClamp == VK_TRUE;
    report->optional[0] = base.logicOp == VK_TRUE;
    report->optional[1] = base.pipelineStatisticsQuery == VK_TRUE;
    uint32_t count = 0;
    R_REQUIRE(report, vkEnumerateDeviceExtensionProperties(physical, NULL, &count, NULL));
    if (count > R_MAX_EXTENSIONS)
        return r_fail(report, "extension_enumeration_bound", VK_ERROR_UNKNOWN);
    VkExtensionProperties extensions[R_MAX_EXTENSIONS];
    R_REQUIRE(report, vkEnumerateDeviceExtensionProperties(physical, NULL, &count, extensions));
    report->required[2] = r_has_extension(extensions, count, VK_KHR_PUSH_DESCRIPTOR_EXTENSION_NAME);
    int dynamic3 = r_has_extension(extensions, count, VK_EXT_EXTENDED_DYNAMIC_STATE_3_EXTENSION_NAME);
    int dynamic2 = r_has_extension(extensions, count, VK_EXT_EXTENDED_DYNAMIC_STATE_2_EXTENSION_NAME);
    uint32_t queues_count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &queues_count, NULL);
    if (queues_count == 0 || queues_count > R_MAX_QUEUES)
        return r_fail(report, "queue_enumeration_bound", VK_ERROR_UNKNOWN);
    VkQueueFamilyProperties queues[R_MAX_QUEUES];
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &queues_count, queues);
    const VkQueueFlags both = VK_QUEUE_GRAPHICS_BIT | VK_QUEUE_COMPUTE_BIT;
    for (uint32_t i = 0; i < queues_count; ++i) {
        if (queues[i].queueCount > 0 && (queues[i].queueFlags & both) == both) {
            report->required[1] = 1; report->queue_family = i; break;
        }
    }
    report->required[4] = r_format(physical, VK_FORMAT_D24_UNORM_S8_UINT,
        VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT |
        VK_IMAGE_USAGE_TRANSFER_DST_BIT, VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT |
        VK_FORMAT_FEATURE_TRANSFER_SRC_BIT | VK_FORMAT_FEATURE_TRANSFER_DST_BIT);
    report->required[5] = r_format(physical, VK_FORMAT_R8G8B8A8_UNORM,
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_STORAGE_BIT |
        VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT |
        VK_IMAGE_USAGE_TRANSFER_DST_BIT, VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
        VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BLEND_BIT | VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT |
        VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT | VK_FORMAT_FEATURE_SAMPLED_IMAGE_FILTER_LINEAR_BIT |
        VK_FORMAT_FEATURE_TRANSFER_SRC_BIT | VK_FORMAT_FEATURE_TRANSFER_DST_BIT);
    /* CodexAstraUlt: Never append unsupported extension structures to a feature
     * query or infer Vulkan13 bits from its version number. Instance1.0 still
     * produces useful baseline evidence, with advanced requirements unmet. */
    if (report->instance_api >= VK_API_VERSION_1_1) {
        PFN_vkGetPhysicalDeviceFeatures2 get_features =
            (PFN_vkGetPhysicalDeviceFeatures2)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceFeatures2");
        PFN_vkGetPhysicalDeviceProperties2 get_properties =
            (PFN_vkGetPhysicalDeviceProperties2)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceProperties2");
        if (!get_features || !get_properties)
            return r_fail(report, "features2_properties2_entrypoints", VK_ERROR_INITIALIZATION_FAILED);
        VkPhysicalDeviceVulkan13Features f13 = { .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES };
        VkPhysicalDeviceExtendedDynamicState3FeaturesEXT f3 = {
            .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTENDED_DYNAMIC_STATE_3_FEATURES_EXT };
        VkPhysicalDeviceExtendedDynamicState2FeaturesEXT f2 = {
            .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTENDED_DYNAMIC_STATE_2_FEATURES_EXT };
        VkPhysicalDeviceFeatures2 features = { .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2 };
        if (report->required[0]) { f13.pNext = features.pNext; features.pNext = &f13; }
        if (dynamic3) { f3.pNext = features.pNext; features.pNext = &f3; }
        if (dynamic2) { f2.pNext = features.pNext; features.pNext = &f2; }
        get_features(physical, &features);
        report->required[6] = f13.dynamicRendering == VK_TRUE;
        report->required[7] = f13.synchronization2 == VK_TRUE;
        report->required[8] = f13.pipelineCreationCacheControl == VK_TRUE;
        report->optional[2] = dynamic3 && f3.extendedDynamicState3ColorBlendEnable &&
            f3.extendedDynamicState3ColorBlendEquation && f3.extendedDynamicState3ColorWriteMask;
        report->optional[3] = report->optional[2] && report->optional[0] && dynamic2 &&
            f2.extendedDynamicState2LogicOp && f3.extendedDynamicState3LogicOpEnable;
        VkPhysicalDevicePushDescriptorPropertiesKHR push = {
            .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PUSH_DESCRIPTOR_PROPERTIES_KHR };
        VkPhysicalDeviceProperties2 props = {
            .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
            .pNext = report->required[2] ? &push : NULL };
        get_properties(physical, &props);
        report->max_push = push.maxPushDescriptors;
        report->required[9] = report->max_push >= 8;
    }
    for (uint32_t i = 0; i < R_REQUIRED; ++i)
        if (!report->required[i]) { report->status = "unsupported"; return 0; }
    return 1;
}

/* CodexAstraUlt: All mapped allocations handle non-coherent memory explicitly;
 * requirement sizes are checked before allocation and all partial objects owned. */
static int r_memory_type(RResources *r, uint32_t allowed, VkMemoryPropertyFlags flags,
                          uint32_t *index) {
    for (uint32_t i = 0; i < r->memory.memoryTypeCount; ++i) {
        if ((allowed & (1u << i)) &&
            (r->memory.memoryTypes[i].propertyFlags & flags) == flags) {
            *index = i; return 1;
        }
    }
    return 0;
}
static int r_allocate(RResources *r, RReport *report, VkMemoryRequirements req,
                       VkMemoryPropertyFlags required, VkMemoryPropertyFlags preferred,
                       VkDeviceMemory *memory, int *coherent) {
    uint32_t index;
    if (req.size == 0 || req.size > R_ALLOCATION_LIMIT)
        return r_fail(report, "representative_allocation_bound", VK_ERROR_OUT_OF_DEVICE_MEMORY);
    if (!r_memory_type(r, req.memoryTypeBits, required | preferred, &index) &&
        !r_memory_type(r, req.memoryTypeBits, required, &index))
        return r_fail(report, "representative_memory_type", VK_ERROR_FEATURE_NOT_PRESENT);
    if (coherent) *coherent = (r->memory.memoryTypes[index].propertyFlags &
                              VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) != 0;
    VkMemoryAllocateInfo info = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        .allocationSize = req.size, .memoryTypeIndex = index };
    R_REQUIRE(report, vkAllocateMemory(r->device, &info, NULL, memory));
    return 1;
}
static int r_image(RResources *r, RReport *report, RImage *image, VkFormat format,
                    uint32_t width, uint32_t height, VkImageUsageFlags usage,
                    VkImageAspectFlags aspects) {
    VkImageCreateInfo info = { .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType = VK_IMAGE_TYPE_2D, .format = format, .extent = { width, height, 1 },
        .mipLevels = 1, .arrayLayers = 1, .samples = VK_SAMPLE_COUNT_1_BIT,
        .tiling = VK_IMAGE_TILING_OPTIMAL, .usage = usage,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE, .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED };
    R_REQUIRE(report, vkCreateImage(r->device, &info, NULL, &image->image));
    VkMemoryRequirements requirements;
    vkGetImageMemoryRequirements(r->device, image->image, &requirements);
    if (!r_allocate(r, report, requirements, 0, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                    &image->memory, NULL)) return 0;
    R_REQUIRE(report, vkBindImageMemory(r->device, image->image, image->memory, 0));
    VkImageViewCreateInfo view = { .sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image = image->image, .viewType = VK_IMAGE_VIEW_TYPE_2D, .format = format,
        .subresourceRange = { aspects, 0, 1, 0, 1 } };
    R_REQUIRE(report, vkCreateImageView(r->device, &view, NULL, &image->view));
    return 1;
}
static int r_buffer(RResources *r, RReport *report, RBuffer *buffer,
                     VkDeviceSize size, VkBufferUsageFlags usage) {
    VkBufferCreateInfo info = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size = size, .usage = usage, .sharingMode = VK_SHARING_MODE_EXCLUSIVE };
    R_REQUIRE(report, vkCreateBuffer(r->device, &info, NULL, &buffer->buffer));
    VkMemoryRequirements requirements;
    vkGetBufferMemoryRequirements(r->device, buffer->buffer, &requirements);
    if (requirements.size < size)
        return r_fail(report, "representative_buffer_requirement", VK_ERROR_UNKNOWN);
    if (!r_allocate(r, report, requirements, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT,
                    VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, &buffer->memory,
                    &buffer->coherent)) return 0;
    R_REQUIRE(report, vkBindBufferMemory(r->device, buffer->buffer, buffer->memory, 0));
    R_REQUIRE(report, vkMapMemory(r->device, buffer->memory, 0, VK_WHOLE_SIZE, 0, &buffer->mapped));
    return 1;
}
static int r_flush(RResources *r, RReport *report, RBuffer *buffer, int invalidate) {
    if (buffer->coherent) return 1;
    VkMappedMemoryRange range = { .sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
        .memory = buffer->memory, .offset = 0, .size = VK_WHOLE_SIZE };
    if (invalidate) { R_REQUIRE(report, vkInvalidateMappedMemoryRanges(r->device, 1, &range)); }
    else { R_REQUIRE(report, vkFlushMappedMemoryRanges(r->device, 1, &range)); }
    return 1;
}

/* CodexAstraUlt: Enable exactly the required renderer feature family after
 * checking support. Optional blend/logic/statistics capabilities are inventory
 * only in this fixture and are deliberately not advertised as executed. */
static int r_create(RResources *r, RReport *report, VkPhysicalDevice physical) {
    float priority = 1.0f;
    VkDeviceQueueCreateInfo queue = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        .queueFamilyIndex = report->queue_family, .queueCount = 1, .pQueuePriorities = &priority };
    VkPhysicalDeviceVulkan13Features features13 = {
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES,
        .dynamicRendering = VK_TRUE, .synchronization2 = VK_TRUE,
        .pipelineCreationCacheControl = VK_TRUE };
    VkPhysicalDeviceFeatures features = { .depthClamp = VK_TRUE };
    const char *extension = VK_KHR_PUSH_DESCRIPTOR_EXTENSION_NAME;
    VkDeviceCreateInfo device = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        .pNext = &features13, .queueCreateInfoCount = 1, .pQueueCreateInfos = &queue,
        .enabledExtensionCount = 1, .ppEnabledExtensionNames = &extension,
        .pEnabledFeatures = &features };
    R_REQUIRE(report, vkCreateDevice(physical, &device, NULL, &r->device));
    vkGetDeviceQueue(r->device, report->queue_family, 0, &r->queue);
    vkGetPhysicalDeviceMemoryProperties(physical, &r->memory);
#define R_LOAD(field, type, name) do { r->field = (type)vkGetDeviceProcAddr(r->device, name); \
    if (!r->field) return r_fail(report, name "_entrypoint", VK_ERROR_INITIALIZATION_FAILED); } while (0)
    R_LOAD(begin_rendering, PFN_vkCmdBeginRendering, "vkCmdBeginRendering");
    R_LOAD(end_rendering, PFN_vkCmdEndRendering, "vkCmdEndRendering");
    R_LOAD(barrier, PFN_vkCmdPipelineBarrier2, "vkCmdPipelineBarrier2");
    R_LOAD(stencil_op, PFN_vkCmdSetStencilOp, "vkCmdSetStencilOp");
    R_LOAD(push, PFN_vkCmdPushDescriptorSetKHR, "vkCmdPushDescriptorSetKHR");
    R_LOAD(submit, PFN_vkQueueSubmit2, "vkQueueSubmit2");
#undef R_LOAD
    if (!r_image(r, report, &r->color, VK_FORMAT_R8G8B8A8_UNORM, R_WIDTH, R_HEIGHT,
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
        VK_IMAGE_ASPECT_COLOR_BIT) ||
        !r_image(r, report, &r->depth, VK_FORMAT_D24_UNORM_S8_UINT, R_WIDTH, R_HEIGHT,
        VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
        VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT) ||
        !r_image(r, report, &r->texture, VK_FORMAT_R8G8B8A8_UNORM, 2, 1,
        VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT,
        VK_IMAGE_ASPECT_COLOR_BIT) ||
        !r_buffer(r, report, &r->readback, R_BYTES, VK_BUFFER_USAGE_TRANSFER_DST_BIT) ||
        !r_buffer(r, report, &r->upload, 8, VK_BUFFER_USAGE_TRANSFER_SRC_BIT) ||
        !r_buffer(r, report, &r->uniform, 16, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT) ||
        !r_buffer(r, report, &r->compute_result, R_WORDS * sizeof(uint32_t),
                  VK_BUFFER_USAGE_STORAGE_BUFFER_BIT)) return 0;
    const uint8_t texture[8] = { 255, 0, 255, 255, 0, 255, 255, 255 };
    const float uniform[4] = { 1, 1, 0, 1 };
    memcpy(r->upload.mapped, texture, sizeof(texture));
    memcpy(r->uniform.mapped, uniform, sizeof(uniform));
    memset(r->compute_result.mapped, 0xff, R_WORDS * sizeof(uint32_t));
    if (!r_flush(r, report, &r->upload, 0) || !r_flush(r, report, &r->uniform, 0) ||
        !r_flush(r, report, &r->compute_result, 0)) return 0;
    VkSamplerCreateInfo sampler = { .sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter = VK_FILTER_NEAREST, .minFilter = VK_FILTER_NEAREST,
        .mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE, .maxLod = 0 };
    R_REQUIRE(report, vkCreateSampler(r->device, &sampler, NULL, &r->sampler));
    VkCommandPoolCreateInfo pool = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
        .queueFamilyIndex = report->queue_family };
    R_REQUIRE(report, vkCreateCommandPool(r->device, &pool, NULL, &r->pool));
    VkCommandBufferAllocateInfo command = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool = r->pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1 };
    R_REQUIRE(report, vkAllocateCommandBuffers(r->device, &command, &r->command));
    VkFenceCreateInfo fence = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    R_REQUIRE(report, vkCreateFence(r->device, &fence, NULL, &r->fence));
    return 1;
}

/* CodexAstraUlt: The dynamic-rendering graphics pipeline uses a pushed sampled
 * texture and uniform, real D24S8 tests and depth clamping. A separate compute
 * pipeline exercises the same graphics+compute queue with storage image/buffer
 * descriptors. Cache-control is enabled and used by EARLY_RETURN_ON_FAILURE. */
static int r_pipelines(RResources *r, RReport *report) {
    const uint32_t *codes[3] = { droidds_renderer_vert_spv,
        droidds_renderer_frag_spv, droidds_renderer_comp_spv };
    const size_t sizes[3] = { sizeof(droidds_renderer_vert_spv),
        sizeof(droidds_renderer_frag_spv), sizeof(droidds_renderer_comp_spv) };
    for (uint32_t i = 0; i < 3; ++i) {
        VkShaderModuleCreateInfo module = { .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
            .codeSize = sizes[i], .pCode = codes[i] };
        R_REQUIRE(report, vkCreateShaderModule(r->device, &module, NULL, &r->shaders[i]));
    }
    for (uint32_t i = 0; i < 2; ++i) {
        VkShaderStageFlags stage = i == 0 ? VK_SHADER_STAGE_FRAGMENT_BIT : VK_SHADER_STAGE_COMPUTE_BIT;
        VkDescriptorSetLayoutBinding bindings[2] = {
            { .binding = 0, .descriptorType = i == 0 ? VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER :
                VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1, .stageFlags = stage },
            { .binding = 1, .descriptorType = i == 0 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER :
                VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .descriptorCount = 1, .stageFlags = stage }
        };
        VkDescriptorSetLayoutCreateInfo set = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
            .flags = VK_DESCRIPTOR_SET_LAYOUT_CREATE_PUSH_DESCRIPTOR_BIT_KHR,
            .bindingCount = 2, .pBindings = bindings };
        R_REQUIRE(report, vkCreateDescriptorSetLayout(r->device, &set, NULL, &r->sets[i]));
        VkPushConstantRange push = { VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, 8 };
        VkPipelineLayoutCreateInfo layout = { .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            .setLayoutCount = 1, .pSetLayouts = &r->sets[i],
            .pushConstantRangeCount = i == 0 ? 1u : 0u, .pPushConstantRanges = i == 0 ? &push : NULL };
        R_REQUIRE(report, vkCreatePipelineLayout(r->device, &layout, NULL, &r->layouts[i]));
    }
    VkPipelineShaderStageCreateInfo stages[2] = {
        { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
          .stage = VK_SHADER_STAGE_VERTEX_BIT, .module = r->shaders[0], .pName = "main" },
        { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
          .stage = VK_SHADER_STAGE_FRAGMENT_BIT, .module = r->shaders[1], .pName = "main" }
    };
    VkPipelineVertexInputStateCreateInfo vertex = { .sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO };
    VkPipelineInputAssemblyStateCreateInfo assembly = { .sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
        .topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST };
    VkViewport viewport = { 0, 0, R_WIDTH, R_HEIGHT, 0, 1 };
    VkRect2D scissor = { { 0, 0 }, { R_WIDTH, R_HEIGHT } };
    VkPipelineViewportStateCreateInfo viewport_state = { .sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
        .viewportCount = 1, .pViewports = &viewport, .scissorCount = 1, .pScissors = &scissor };
    VkPipelineRasterizationStateCreateInfo raster = { .sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
        .depthClampEnable = VK_TRUE, .polygonMode = VK_POLYGON_MODE_FILL,
        .cullMode = VK_CULL_MODE_NONE, .frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE, .lineWidth = 1 };
    VkPipelineMultisampleStateCreateInfo multi = { .sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
        .rasterizationSamples = VK_SAMPLE_COUNT_1_BIT };
    VkPipelineDepthStencilStateCreateInfo depth = { .sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO,
        .depthTestEnable = VK_TRUE, .depthWriteEnable = VK_TRUE, .depthCompareOp = VK_COMPARE_OP_LESS,
        .stencilTestEnable = VK_TRUE, .minDepthBounds = 0, .maxDepthBounds = 1 };
    VkPipelineColorBlendAttachmentState color = { .colorWriteMask = VK_COLOR_COMPONENT_R_BIT |
        VK_COLOR_COMPONENT_G_BIT | VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT };
    VkPipelineColorBlendStateCreateInfo blend = { .sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
        .attachmentCount = 1, .pAttachments = &color };
    VkDynamicState states[] = { VK_DYNAMIC_STATE_SCISSOR, VK_DYNAMIC_STATE_STENCIL_OP,
        VK_DYNAMIC_STATE_STENCIL_REFERENCE, VK_DYNAMIC_STATE_STENCIL_COMPARE_MASK, VK_DYNAMIC_STATE_STENCIL_WRITE_MASK };
    VkPipelineDynamicStateCreateInfo dynamic = { .sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
        .dynamicStateCount = (uint32_t)(sizeof(states) / sizeof(states[0])), .pDynamicStates = states };
    VkFormat color_format = VK_FORMAT_R8G8B8A8_UNORM;
    VkPipelineRenderingCreateInfo rendering = { .sType = VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO,
        .colorAttachmentCount = 1, .pColorAttachmentFormats = &color_format,
        .depthAttachmentFormat = VK_FORMAT_D24_UNORM_S8_UINT,
        .stencilAttachmentFormat = VK_FORMAT_D24_UNORM_S8_UINT };
    VkGraphicsPipelineCreateInfo graphics = { .sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
        .pNext = &rendering, .flags = VK_PIPELINE_CREATE_EARLY_RETURN_ON_FAILURE_BIT,
        .stageCount = 2, .pStages = stages, .pVertexInputState = &vertex,
        .pInputAssemblyState = &assembly, .pViewportState = &viewport_state,
        .pRasterizationState = &raster, .pMultisampleState = &multi,
        .pDepthStencilState = &depth, .pColorBlendState = &blend, .pDynamicState = &dynamic,
        .layout = r->layouts[0], .basePipelineIndex = -1 };
    R_REQUIRE(report, vkCreateGraphicsPipelines(r->device, VK_NULL_HANDLE, 1, &graphics, NULL, &r->pipelines[0]));
    ++report->pipelines;
    VkComputePipelineCreateInfo compute = { .sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
        .flags = VK_PIPELINE_CREATE_EARLY_RETURN_ON_FAILURE_BIT,
        .stage = { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            .stage = VK_SHADER_STAGE_COMPUTE_BIT, .module = r->shaders[2], .pName = "main" },
        .layout = r->layouts[1], .basePipelineIndex = -1 };
    R_REQUIRE(report, vkCreateComputePipelines(r->device, VK_NULL_HANDLE, 1, &compute, NULL, &r->pipelines[1]));
    ++report->pipelines;
    return 1;
}

/* CodexAstraUlt: Every GPU read/write transition uses synchronization2. Host
 * memory access follows a real queue-submit2 fence and cache invalidation. */
static void r_image_barrier(RResources *r, RImage *image, VkImageAspectFlags aspect,
                            VkImageLayout old_layout, VkImageLayout new_layout,
                            VkPipelineStageFlags2 source, VkAccessFlags2 source_access,
                            VkPipelineStageFlags2 destination, VkAccessFlags2 destination_access) {
    VkImageMemoryBarrier2 barrier = { .sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2,
        .srcStageMask = source, .srcAccessMask = source_access,
        .dstStageMask = destination, .dstAccessMask = destination_access,
        .oldLayout = old_layout, .newLayout = new_layout,
        .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED, .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .image = image->image, .subresourceRange = { aspect, 0, 1, 0, 1 } };
    VkDependencyInfo dependency = { .sType = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
        .imageMemoryBarrierCount = 1, .pImageMemoryBarriers = &barrier };
    r->barrier(r->command, &dependency);
}
static void r_buffer_barrier(RResources *r, RBuffer *buffer,
                             VkPipelineStageFlags2 source, VkAccessFlags2 source_access,
                             VkPipelineStageFlags2 destination, VkAccessFlags2 destination_access) {
    VkBufferMemoryBarrier2 barrier = { .sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER_2,
        .srcStageMask = source, .srcAccessMask = source_access,
        .dstStageMask = destination, .dstAccessMask = destination_access,
        .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED, .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .buffer = buffer->buffer, .offset = 0, .size = VK_WHOLE_SIZE };
    VkDependencyInfo dependency = { .sType = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
        .bufferMemoryBarrierCount = 1, .pBufferMemoryBarriers = &barrier };
    r->barrier(r->command, &dependency);
}
static int r_begin(RResources *r, RReport *report) {
    R_REQUIRE(report, vkResetFences(r->device, 1, &r->fence));
    R_REQUIRE(report, vkResetCommandBuffer(r->command, 0));
    VkCommandBufferBeginInfo begin = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT };
    R_REQUIRE(report, vkBeginCommandBuffer(r->command, &begin));
    return 1;
}
static int r_submit(RResources *r, RReport *report) {
    R_REQUIRE(report, vkEndCommandBuffer(r->command));
    VkCommandBufferSubmitInfo command = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_SUBMIT_INFO,
        .commandBuffer = r->command };
    VkSubmitInfo2 submit = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO_2,
        .commandBufferInfoCount = 1, .pCommandBufferInfos = &command };
    r->submitted = 1;
    R_REQUIRE(report, r->submit(r->queue, 1, &submit, r->fence));
    R_REQUIRE(report, vkWaitForFences(r->device, 1, &r->fence, VK_TRUE, UINT64_MAX));
    r->submitted = 0;
    return 1;
}
static int r_upload(RResources *r, RReport *report) {
    if (!r_begin(r, report)) return 0;
    r_buffer_barrier(r, &r->upload, VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_WRITE_BIT,
        VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
    r_image_barrier(r, &r->texture, VK_IMAGE_ASPECT_COLOR_BIT,
        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
        VK_PIPELINE_STAGE_2_NONE, 0, VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
    VkBufferImageCopy copy = { .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
        .imageExtent = { 2, 1, 1 } };
    vkCmdCopyBufferToImage(r->command, r->upload.buffer, r->texture.image,
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copy);
    r_image_barrier(r, &r->texture, VK_IMAGE_ASPECT_COLOR_BIT,
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_GENERAL,
        VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_READ_BIT);
    return r_submit(r, report);
}
static void r_draw(RResources *r, float depth, uint32_t mode, uint32_t x, uint32_t width,
                    VkCompareOp stencil_compare, uint32_t reference) {
    VkRect2D scissor = { { (int32_t)x, 0 }, { width, R_HEIGHT } };
    struct { float depth; uint32_t mode; } push = { depth, mode };
    vkCmdSetScissor(r->command, 0, 1, &scissor);
    r->stencil_op(r->command, VK_STENCIL_FACE_FRONT_AND_BACK, VK_STENCIL_OP_KEEP,
        VK_STENCIL_OP_REPLACE, VK_STENCIL_OP_KEEP, stencil_compare);
    vkCmdSetStencilReference(r->command, VK_STENCIL_FACE_FRONT_AND_BACK, reference);
    vkCmdSetStencilCompareMask(r->command, VK_STENCIL_FACE_FRONT_AND_BACK, 0xff);
    vkCmdSetStencilWriteMask(r->command, VK_STENCIL_FACE_FRONT_AND_BACK, 0xff);
    vkCmdPushConstants(r->command, r->layouts[0], VK_SHADER_STAGE_VERTEX_BIT |
        VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(push), &push);
    vkCmdDraw(r->command, 3, 1, 0, 0);
}

/* CodexAstraUlt: The host oracle is independent of GLSL execution: red/blue
 * halves after real accepted/rejected depth+stencil draws, then red/green halves
 * from a triangle outside the normal near plane that depth clamping must keep. */
static uint32_t r_compare_pixels(const uint8_t *data, uint32_t pattern) {
    uint32_t mismatches = 0;
    for (uint32_t y = 0; y < R_HEIGHT; ++y) {
        for (uint32_t x = 0; x < R_WIDTH; ++x) {
            int right = x >= R_WIDTH / 2;
            const uint8_t expected[4] = { right ? 0 : 255,
                right && pattern == 1 ? 255 : 0, right && pattern == 0 ? 255 : 0, 255 };
            if (memcmp(data + (y * R_WIDTH + x) * 4, expected, 4) != 0) ++mismatches;
        }
    }
    return mismatches;
}
static int r_render(RResources *r, RReport *report, uint32_t pattern) {
    if (!r_begin(r, report)) return 0;
    r_image_barrier(r, &r->color, VK_IMAGE_ASPECT_COLOR_BIT,
        pattern == 0 ? VK_IMAGE_LAYOUT_UNDEFINED : VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        pattern == 0 ? VK_PIPELINE_STAGE_2_NONE : VK_PIPELINE_STAGE_2_TRANSFER_BIT,
        pattern == 0 ? 0 : VK_ACCESS_2_TRANSFER_READ_BIT,
        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    r_image_barrier(r, &r->depth, VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT,
        pattern == 0 ? VK_IMAGE_LAYOUT_UNDEFINED : VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL,
        VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL,
        pattern == 0 ? VK_PIPELINE_STAGE_2_NONE : VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT |
            VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
        pattern == 0 ? 0 : VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
        VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
        VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT);
    r_buffer_barrier(r, &r->uniform, VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_WRITE_BIT,
        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_UNIFORM_READ_BIT);
    if (pattern != 0)
        r_buffer_barrier(r, &r->readback, VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT,
            VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
    VkRenderingAttachmentInfo color = { .sType = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView = r->color.view, .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        .loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR, .storeOp = VK_ATTACHMENT_STORE_OP_STORE,
        .clearValue = { .color = { .float32 = { 0, 0, 0, 0 } } } };
    VkRenderingAttachmentInfo depth = { .sType = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView = r->depth.view, .imageLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL,
        .loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR, .storeOp = VK_ATTACHMENT_STORE_OP_STORE,
        .clearValue = { .depthStencil = { 1.0f, 0 } } };
    VkRenderingInfo rendering = { .sType = VK_STRUCTURE_TYPE_RENDERING_INFO,
        .renderArea = { { 0, 0 }, { R_WIDTH, R_HEIGHT } }, .layerCount = 1,
        .colorAttachmentCount = 1, .pColorAttachments = &color,
        .pDepthAttachment = &depth, .pStencilAttachment = &depth };
    r->begin_rendering(r->command, &rendering);
    vkCmdBindPipeline(r->command, VK_PIPELINE_BIND_POINT_GRAPHICS, r->pipelines[0]);
    VkDescriptorImageInfo image = { .sampler = r->sampler,
        .imageView = r->texture.view, .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
    VkDescriptorBufferInfo uniform = { .buffer = r->uniform.buffer, .offset = 0, .range = 16 };
    VkWriteDescriptorSet writes[2] = {
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstBinding = 0, .descriptorCount = 1,
          .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &image },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstBinding = 1, .descriptorCount = 1,
          .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, .pBufferInfo = &uniform }
    };
    r->push(r->command, VK_PIPELINE_BIND_POINT_GRAPHICS, r->layouts[0], 0, 2, writes);
    uint32_t draws = pattern == 0 ? 4 : 1;
    if (pattern == 0) {
        r_draw(r, 0.5f, 0, 0, R_WIDTH, VK_COMPARE_OP_ALWAYS, 1);
        r_draw(r, 0.75f, 1, 0, R_WIDTH, VK_COMPARE_OP_EQUAL, 1);
        r_draw(r, 0.25f, 1, 0, R_WIDTH, VK_COMPARE_OP_EQUAL, 2);
        r_draw(r, 0.25f, 1, R_WIDTH / 2, R_WIDTH / 2, VK_COMPARE_OP_EQUAL, 1);
    } else r_draw(r, -0.5f, 0, 0, R_WIDTH, VK_COMPARE_OP_ALWAYS, 1);
    r->end_rendering(r->command);
    r_image_barrier(r, &r->color, VK_IMAGE_ASPECT_COLOR_BIT,
        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
        VK_PIPELINE_STAGE_2_TRANSFER_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
    VkBufferImageCopy copy = { .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
        .imageExtent = { R_WIDTH, R_HEIGHT, 1 } };
    vkCmdCopyImageToBuffer(r->command, r->color.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        r->readback.buffer, 1, &copy);
    r_buffer_barrier(r, &r->readback, VK_PIPELINE_STAGE_2_TRANSFER_BIT,
        VK_ACCESS_2_TRANSFER_WRITE_BIT, VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    if (!r_submit(r, report) || !r_flush(r, report, &r->readback, 1)) return 0;
    uint8_t snapshot[R_BYTES];
    memcpy(snapshot, r->readback.mapped, sizeof(snapshot));
    uint32_t mismatches = r_compare_pixels(snapshot, pattern);
    report->draws += draws; report->case_draws[pattern] = draws;
    ++report->readbacks; report->pixels += R_PIXELS; report->mismatches += mismatches;
    report->case_pixels[pattern] = R_PIXELS; report->case_mismatches[pattern] = mismatches;
    if (mismatches) return r_fail(report, "representative_pixel_mismatch", VK_ERROR_UNKNOWN);
    snapshot[0] ^= 1;
    int rejected = r_compare_pixels(snapshot, pattern) == 1;
    snapshot[0] ^= 1;
    ++report->negatives;
    if (!rejected || r_compare_pixels(snapshot, pattern) != 0) {
        report->negative_ok = 0;
        return r_fail(report, "representative_pixel_mutation", VK_ERROR_UNKNOWN);
    }
    return 1;
}
static uint32_t r_compare_words(const uint32_t *words) {
    uint32_t mismatches = 0;
    for (uint32_t i = 0; i < R_WORDS; ++i) {
        uint32_t expected = (i * 3u + 7u) ^ (i % 2u ? 0x00ffffffu : 0xff00ffffu);
        if (words[i] != expected) ++mismatches;
    }
    return mismatches;
}
static int r_compute(RResources *r, RReport *report) {
    if (!r_begin(r, report)) return 0;
    r_buffer_barrier(r, &r->compute_result, VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_WRITE_BIT,
        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    vkCmdBindPipeline(r->command, VK_PIPELINE_BIND_POINT_COMPUTE, r->pipelines[1]);
    VkDescriptorBufferInfo buffer = { .buffer = r->compute_result.buffer,
        .offset = 0, .range = R_WORDS * sizeof(uint32_t) };
    VkDescriptorImageInfo image = { .imageView = r->texture.view, .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
    VkWriteDescriptorSet writes[2] = {
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstBinding = 0, .descriptorCount = 1,
          .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .pBufferInfo = &buffer },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstBinding = 1, .descriptorCount = 1,
          .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .pImageInfo = &image }
    };
    r->push(r->command, VK_PIPELINE_BIND_POINT_COMPUTE, r->layouts[1], 0, 2, writes);
    vkCmdDispatch(r->command, 1, 1, 1);
    r_buffer_barrier(r, &r->compute_result, VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
        VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT, VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    if (!r_submit(r, report) || !r_flush(r, report, &r->compute_result, 1)) return 0;
    uint32_t snapshot[R_WORDS];
    memcpy(snapshot, r->compute_result.mapped, sizeof(snapshot));
    ++report->dispatches; report->words = R_WORDS;
    report->word_mismatches = r_compare_words(snapshot);
    if (report->word_mismatches) return r_fail(report, "representative_compute_mismatch", VK_ERROR_UNKNOWN);
    snapshot[0] ^= 1;
    int rejected = r_compare_words(snapshot) == 1;
    snapshot[0] ^= 1;
    ++report->negatives;
    if (!rejected || r_compare_words(snapshot) != 0) {
        report->negative_ok = 0;
        return r_fail(report, "representative_compute_mutation", VK_ERROR_UNKNOWN);
    }
    return 1;
}

/* CodexAstraUlt: Partial construction is safe to destroy. Submitted work must
 * finish or establish device loss first; a hung driver is left to the external
 * process deadline, never disguised as a passing or safely reclaimed device. */
static void r_destroy_buffer(RResources *r, RBuffer *buffer) {
    if (buffer->mapped) vkUnmapMemory(r->device, buffer->memory);
    if (buffer->buffer) vkDestroyBuffer(r->device, buffer->buffer, NULL);
    if (buffer->memory) vkFreeMemory(r->device, buffer->memory, NULL);
}
static void r_destroy_image(RResources *r, RImage *image) {
    if (image->view) vkDestroyImageView(r->device, image->view, NULL);
    if (image->image) vkDestroyImage(r->device, image->image, NULL);
    if (image->memory) vkFreeMemory(r->device, image->memory, NULL);
}
static void r_destroy(RResources *r) {
    if (!r->device) return;
    if (r->submitted) {
        VkResult idle = vkDeviceWaitIdle(r->device);
        if (idle != VK_SUCCESS && idle != VK_ERROR_DEVICE_LOST) abort();
    }
    if (r->fence) vkDestroyFence(r->device, r->fence, NULL);
    if (r->pool) vkDestroyCommandPool(r->device, r->pool, NULL);
    for (uint32_t i = 0; i < 2; ++i) {
        if (r->pipelines[i]) vkDestroyPipeline(r->device, r->pipelines[i], NULL);
        if (r->layouts[i]) vkDestroyPipelineLayout(r->device, r->layouts[i], NULL);
        if (r->sets[i]) vkDestroyDescriptorSetLayout(r->device, r->sets[i], NULL);
    }
    for (uint32_t i = 0; i < 3; ++i)
        if (r->shaders[i]) vkDestroyShaderModule(r->device, r->shaders[i], NULL);
    if (r->sampler) vkDestroySampler(r->device, r->sampler, NULL);
    r_destroy_buffer(r, &r->compute_result); r_destroy_buffer(r, &r->uniform);
    r_destroy_buffer(r, &r->upload); r_destroy_buffer(r, &r->readback);
    r_destroy_image(r, &r->texture); r_destroy_image(r, &r->depth); r_destroy_image(r, &r->color);
    vkDestroyDevice(r->device, NULL);
}

/* CodexAstraUlt: Names and error strings are fixed source literals, so this
 * bounded serializer contains no unescaped driver/user strings. Missing
 * capabilities remain explicit, even when the basic Vulkan1.0 draws passed. */
typedef struct { char *text; size_t size, used; int failed; } RWriter;
static void r_append(RWriter *w, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void r_append(RWriter *w, const char *format, ...) {
    if (w->failed) return;
    va_list args; va_start(args, format);
    int count = vsnprintf(w->text + w->used, w->size - w->used, format, args);
    va_end(args);
    if (count < 0 || (size_t)count >= w->size - w->used) { w->failed = 1; return; }
    w->used += (size_t)count;
}
static int r_serialize(const RReport *r, char *json, size_t capacity) {
    RWriter w = { json, capacity, 0, 0 };
    r_append(&w, "{\"schema\":1,\"kind\":\"droidds-renderer-probe\",\"contract\":\"zakuro-412900a\","
        "\"status\":\"%s\",\"instance_api_version\":%" PRIu32 ",\"physical_api_version\":%" PRIu32
        ",\"queue_family\":%" PRIu32 ",\"max_push_descriptors\":%" PRIu32 ",\"required\":{",
        r->status, r->instance_api, r->physical_api, r->queue_family, r->max_push);
    for (uint32_t i = 0; i < R_REQUIRED; ++i)
        r_append(&w, "%s\"%s\":%s", i ? "," : "", R_NAMES[i], r->required[i] ? "true" : "false");
    r_append(&w, "},\"missing_required\":[");
    uint32_t missing = 0;
    for (uint32_t i = 0; i < R_REQUIRED; ++i)
        if (!r->required[i]) r_append(&w, "%s\"%s\"", missing++ ? "," : "", R_NAMES[i]);
    r_append(&w, "],\"optional\":{\"logic_op\":%s,\"pipeline_statistics_query\":%s,"
        "\"dynamic_blend\":%s,\"dynamic_logic_op\":%s},\"width\":16,\"height\":16,"
        "\"pipeline_creation_count\":%" PRIu32 ",\"draw_count\":%" PRIu32
        ",\"dispatch_count\":%" PRIu32 ",\"readbacks_completed\":%" PRIu32
        ",\"pixels_checked\":%" PRIu32 ",\"mismatched_pixels\":%" PRIu32
        ",\"compute_words_checked\":%" PRIu32 ",\"compute_word_mismatches\":%" PRIu32
        ",\"negative_checks_completed\":%" PRIu32 ",\"negative_controls_passed\":%s,\"cases\":[",
        r->optional[0] ? "true" : "false", r->optional[1] ? "true" : "false",
        r->optional[2] ? "true" : "false", r->optional[3] ? "true" : "false",
        r->pipelines, r->draws, r->dispatches, r->readbacks, r->pixels, r->mismatches,
        r->words, r->word_mismatches, r->negatives, r->negative_ok && r->negatives == 3 ? "true" : "false");
    const char *names[2] = { "textured_depth_stencil", "depth_clamp" };
    for (uint32_t i = 0; i < 2; ++i) {
        const char *status = r->case_mismatches[i] ? "failed" :
            r->case_pixels[i] == R_PIXELS ? "passed" : "incomplete";
        r_append(&w, "%s{\"name\":\"%s\",\"status\":\"%s\",\"pixels_checked\":%" PRIu32
            ",\"mismatched_pixels\":%" PRIu32 ",\"draw_count\":%" PRIu32 "}",
            i ? "," : "", names[i], status, r->case_pixels[i], r->case_mismatches[i], r->case_draws[i]);
    }
    r_append(&w, "],\"error\":");
    if (r->error) r_append(&w, "{\"step\":\"%s\",\"vk_result\":%d}", r->error, (int)r->result);
    else r_append(&w, "null");
    r_append(&w, "}");
    if (w.failed || w.used > INT32_MAX) { json[0] = '\0'; return -1; }
    return (int)w.used;
}
int dds_renderer_probe_run(VkInstance instance, VkPhysicalDevice physical,
                          uint32_t instance_api, char *json, size_t capacity,
                          int *passed) {
    if (!json || capacity == 0 || !passed) return -1;
    *passed = 0;
    RReport report = { .status = "failed", .instance_api = instance_api, .negative_ok = 1 };
    if (r_capabilities(instance, physical, &report)) {
        RResources resources = {0};
        int ok = r_create(&resources, &report, physical) && r_pipelines(&resources, &report) &&
            r_upload(&resources, &report) && r_render(&resources, &report, 0) &&
            r_render(&resources, &report, 1) && r_compute(&resources, &report);
        r_destroy(&resources);
        if (ok) { report.status = "passed"; *passed = 1; }
    }
    return r_serialize(&report, json, capacity);
}
