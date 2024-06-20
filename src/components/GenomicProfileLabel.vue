<template>
    <span :title="annotations?.length > 0 ? annotations : undefined">{{ variantString }}<span v-if="!isLast">,&nbsp;</span></span>
</template>
<script lang="ts">
export default {
    props: {
        variantString: {
            type: String,
            required: true,
        },
        annotations: {
            type: Array<String>,
            required: false,
        },
        isLast: {
            type: Boolean,
            required: true,
        },
    },
};
</script>