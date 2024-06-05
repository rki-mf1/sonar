import type { FilterGroupFilters, FilterGroupRoot } from '@/util/types'
import Axios from 'axios'
import qs from 'qs'

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
    BACKEND_ADDRESS = "http://localhost:8000/api/"

    static instance: API
    static getInstance(): API {
        if (!API.instance) {
            API.instance = new API()
            API.instance.fillAuthenticationHeader()
        }
        return API.instance
    }
    fillAuthenticationHeader() {
        Axios.defaults.headers.common = {
            Authorization: `Token M2BtbMGQMHsPg9CwPjIuDdWNfv3NkJL8`,
            Accept: 'application/json; version=1.0.1'
        }
    }
    async getRequestFullUrl(url: string, params: JSON, suppressError: boolean) {
        const stringifiedParams = qs.stringify(params)
        return Axios.get(url, {
            data: stringifiedParams,
            timeout: this.TIMEOUT
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
    getSampleGenomes(params: FilterGroupRoot) {
        const queryString = this.parseQueryString(params)
        const url = `samples/genomes/${queryString}`
        return this.getRequest(url, {}, false)
    }
    async getSampleGenomesExport(params: FilterGroupRoot) {
        params["csv_stream"] = true
        const queryString = this.parseQueryString(params)
        const url = `samples/genomes/${queryString}`
        this.getRequest(url, {}, false).then(
            response => {
                const url = window.URL.createObjectURL(new Blob([response], { type: "text/csv" }));
                const link = document.createElement("a");
                link.href = url;
                link.setAttribute(
                    "download",
                    "export.csv"
                );
                document.body.appendChild(link);
                link.click();
            }
        )
    }
    getSampleGenomePropertyOptions() {
        return this.getRequest(`properties/distinct_property_names`, {}, false)
    }

    getSampleStatistics() {
        return this.getRequest(`samples/statistics`, {}, false)
    }

    getSampleGenomePropertyValueOptions(propertyName: string) {
        return this.getRequest(`properties/distinct_properties/?property_name=${propertyName}`, {}, false)
    }
    getRepliconAccessionOptions() {
        const url = `replicons/distinct_accessions/`
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
}