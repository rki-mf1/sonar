import type { FilterGroupFilters, FilterGroupRoot } from '@/util/types'
import axios from 'axios'
import { saveAs } from 'file-saver';
import qs from 'qs'
import { Workbook } from 'exceljs';

export default class API {
    CODE_OK = 200
    CODE_CREATED = 201
    CODE_NO_CONTENT = 204
    CODE_BAD_REQUEST = 400
    CODE_UNAUTHORIZED = 401
    CODE_FORBIDDEN = 403
    CODE_NOT_FOUND = 404
    CODE_TIMEOUT = 'ECONNABORTED'
    METHOD_NOT_ALLOWED = 405
    CODE_CONFLICT = 409
    CODE_INTERNAL_SERVER_ERROR = 500

    TIMEOUT = 50000;
    BACKEND_ADDRESS = import.meta.env.VITE_SONAR_BACKEND_ADDRESS

    static instance: API
    static getInstance(): API {
        if (!API.instance) {
            API.instance = new API()
            API.instance.fillAuthenticationHeader()
        }
        return API.instance
    }
    fillAuthenticationHeader() {
        axios.defaults.headers.common = {
            Authorization: `Token M2BtbMGQMHsPg9CwPjIuDdWNfv3NkJL8`,
            Accept: 'application/json; version=1.0.1'
        }
    }
    async getRequestFullUrl(url: string, params: JSON, suppressError: boolean) {
        const stringifiedParams = qs.stringify(params)
        return axios.get(url, {
            data: stringifiedParams,
            timeout: this.TIMEOUT,
        })
            .then((result) => result.data)
            .catch((error) => {
                if (error.response?.status == this.CODE_UNAUTHORIZED) {
                    console.log('Unauthorized', `Unauthorized on \n ${url}.`)
                    return
                }
                if (!suppressError) {
                    switch (error.code) {
                        case this.CODE_TIMEOUT: {
                            console.log('Timeout', `Request timed out on \n ${url}.`)
                            break
                        }
                        case this.CODE_INTERNAL_SERVER_ERROR: {
                            console.log('500', `Internal Server Error  on \n ${url}.`)
                            break
                        }
                        case this.CODE_NOT_FOUND: {
                            console.log('404', `Not found on \n ${url}.`)
                            break
                        }
                    }
                    return error
                }
            })
    }
    getRequest(url: string, params, suppressError: boolean) {
        return this.getRequestFullUrl(`${this.BACKEND_ADDRESS}${url}`, params, suppressError)
    }
    getSampleGenomes(filters: FilterGroupRoot, params) {
        let url = `samples/genomes/?`
        for (const key of Object.keys(params)) {
            url += `${key}=${params[key]}&`
        }
        url = url.slice(0, -1)
        if (Object.keys(filters).length > 0) {
            url += this.parseQueryString(filters).replace('?', '&')
        }
        return this.getRequest(url, {}, false)
    }

    getSingleSampleGenome(name: string) {
        return this.getRequest(`samples/genomes/?name=${name}`, {}, false)
    }

    getFilteredStatistics(params: FilterGroupRoot) {
        const queryString = this.parseQueryString(params)
        const url = `samples/filtered_statistics/${queryString}`
        return this.getRequest(url, {}, false)
    }
    async getSampleGenomesExport(params: FilterGroupRoot, columns: string[], xls = true) {
        const exportColumns = ['name', ...columns]
        const queryString = this.parseQueryString(params)
        let url = `${this.BACKEND_ADDRESS}samples/genomes/${queryString}`
        url += `&columns=${exportColumns.join(',')}`
        url += `&csv_stream=true`
        const response = await axios.get(url, {
            responseType: 'stream',
            adapter: 'fetch'
        })
        const stream = response.data;
        if (xls) {
            const reader = stream.pipeThrough(new TextDecoderStream()).getReader();
            this.saveAsXLSX(reader, exportColumns)
            return
        }
        const chunks = []
        const outStream = new WritableStream({
            write(chunk) {
                chunks.push(chunk)
            },
            close() {
                // console.log('Stream closed')
            }
        })
        await stream.pipeThrough(new TextDecoderStream()).pipeTo(outStream)
        const arrayBuffer = await new Blob(chunks).arrayBuffer()
        const blob = new Blob([arrayBuffer])
        saveAs(blob, 'export.csv')
    }

    async saveAsXLSX(reader, columns) {
        const workbook = new Workbook();
        const worksheet = workbook.addWorksheet('Sheet 1');
        worksheet.columns = columns.map((c) => ({ header: c, key: c, width: 20 }));
        let row = 1;
        let data = '' as string;
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            data += value;
            if (data && data.includes('\n')) {
                const lines = data.split('\n');
                data = lines.pop();
                for (const line of lines) {
                    const values = line.split(';');
                    const rowValues = {};
                    columns.forEach((c, i) => {
                        rowValues[c] = values[i];
                    });
                    worksheet.addRow(rowValues, row);
                    row++;
                }
            }
        }
        const buffer = await workbook.xlsx.writeBuffer();
        saveAs(new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), 'export.xlsx')

    }


    getSampleGenomePropertyOptions() {
        return this.getRequest(`properties/distinct_property_names`, {}, false)
    }

    getSampleGenomePropertyOptionsAndTypes() {
        return this.getRequest(`properties/get_all_properties`, {}, false)
    }

    getSampleStatistics() {
        return this.getRequest(`samples/statistics`, {}, false)
    }

    getSampleGenomePropertyValueOptions(propertyName: string) {
        // get unique value2 of each property_name 
        return this.getRequest(`properties/distinct_properties/?property_name=${propertyName}`, {}, false)
    }
    getRepliconAccessionOptions() {
        const url = `replicons/distinct_accessions/`
        return this.getRequest(url, {}, false)
    }
    getLineageOptions() {
        const url = `lineages/distinct_lineages/`
        return this.getRequest(url, {}, false)
    }
    getGeneSymbolOptions() {
        return this.getRequest(`genes/distinct_gene_symbols`, {}, false)
    }
    parseQueryString(query) {
        if (Object.keys(query).length > 0) {
            return (
                "?" +
                Object.keys(query)
                    .map(function (k) {
                        let value = JSON.stringify(query[k])
                        if (value === undefined || value === null) {
                            value = query[k].toString()
                        }
                        const param = (
                            encodeURIComponent(k.toString().trim()) +
                            "=" +
                            encodeURIComponent(value)
                        )
                        return param;
                    })
                    .join("&")
            );
        } else return "";
    }
    uniqueMutationCount() {
        return this.getRequest(`mutations/distinct_mutations_count`, {}, false)
    }
}
