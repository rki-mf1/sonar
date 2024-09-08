<template>
    <OverlayPanel :ref="op">
        <div class="flex flex-column gap-3 w-25rem">
            <div>
                <span class="font-medium text-900 block mb-2">
                    Range input (2,5)
                </span>

            </div>
        </div>
    </OverlayPanel>
</template>

<script>
export default {
    name: "ExampleUsage",
    props: {
        op: {
            type: Object,
            required: true, // The ref is required
        }
    }
};
</script>