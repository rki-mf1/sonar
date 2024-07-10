<template>
    <div v-if="selectedRow">
        <p v-for="(value, key) in selectedRow" :key="key">
        <p v-if="allColumns.includes(key)">
            <template v-if="key === 'genomic_profiles'">
                <strong>{{ key }}: </strong>
                <div style="white-space: normal; word-wrap: break-word;">
                    <GenomicProfileLabel v-for="(variant, index) in Object.keys(value)" :variantString="variant"
                        :annotations="value[variant]" :isLast="index === Object.keys(value).length - 1" />
                </div>
            </template>
            <template v-else-if="key === 'proteomic_profiles'">
                <strong>{{ key }}: </strong>
                <div style="white-space: normal; word-wrap: break-word;">
                    <GenomicProfileLabel v-for="(variant, index) in value" :variantString="variant"
                        :isLast="index === Object.keys(value).length - 1" />
                </div>
            </template>
            <template v-else-if="key === 'properties'">
                <strong>{{ key }}:</strong>
                <div v-for="item in value" :key="item.name">
                    <div v-if="item.name === 'lineage'">
                        <strong>&nbsp;&nbsp;&nbsp;{{ item.name }}:</strong> {{ item.value }} (<a
                            :href="'https://outbreak.info/situation-reports?pango=' + item.value"
                            target="_blank">outbreak.info</a>)
                    </div>
                    <div v-else>
                        <strong>&nbsp;&nbsp;&nbsp;{{ item.name }}:</strong> {{ item.value }}
                    </div>
                </div>
            </template>
            <template v-else>
                <strong>{{ key }}:</strong> {{ value }}
            </template>
        </p>
        </p>
    </div>

</template>

<script lang="ts">

import type { PropType } from 'vue';

export default {
    name: "SampleDetails",
    props: {
        selectedRow: {
            // type: Object as PropType<number>, 
            required: true,
        },
        allColumns: {
            // type: Object as PropType<number>, 
            required: true,
        }
    }
}
</script>

<style scoped></style>