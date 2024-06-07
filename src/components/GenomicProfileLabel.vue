<template>
    <span :title="annotations?.length > 0 ? annotations : undefined">{{ variantString }},&nbsp;</span>
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
    },
};
</script>