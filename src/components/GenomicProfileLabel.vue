<template>
    <span :title="annotations?.length > 0 ? annotations : undefined"
    :style="{ color: variantColor}">{{ variantString }}<span v-if="!isLast">,&nbsp;</span></span>
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
    computed: {
        variantColor(): string {
            if (this.annotations && this.annotations.length > 0) {
                if (this.annotations.some(annotation => annotation.includes('HIGH'))) {
                    return 'red';
                } else if (this.annotations.some(annotation => annotation.includes('MODERATE'))) {
                    return 'orange';
                } else if (this.annotations.some(annotation => annotation.includes('LOW'))) {
                    return 'green';
                }
            }
            return '';
        },
    }
};
</script>