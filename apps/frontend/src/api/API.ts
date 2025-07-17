import type { FilterGroupRoot } from '@/util/types'
import axios from 'axios'
import { saveAs } from 'file-saver'
import qs from 'qs'
import * as ExcelJS from 'exceljs'

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

  TIMEOUT = 50000
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
      Accept: 'application/json; version=1.0.1',
    }
  }
  async getRequestFullUrl(url: string, params: Record<string, unknown>, suppressError: boolean) {
    return axios
      .get(url, {
        params,
        paramsSerializer: (params) => qs.stringify(params, { arrayFormat: 'repeat' }),
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
  getRequest(url: string, params: Record<string, unknown> = {}, suppressError: boolean) {
    const fullUrl = `${this.BACKEND_ADDRESS}${url}`
    return this.getRequestFullUrl(fullUrl, params, suppressError)
  }

  getDatasetOptions() {
    return this.getRequest(`references/dataset_options/`, {}, false)
  }

  getSampleGenomes(filters: FilterGroupRoot, params: Record<string, string | number | boolean>) {
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

  getFilteredStatisticsPlots(params: FilterGroupRoot) {
    const queryString = this.parseQueryString(params)
    const url = `samples/filtered_statistics_plots/${queryString}`
    return this.getRequest(url, {}, false)
  }

  async getSampleGenomesExport(
    params: FilterGroupRoot,
    columns: string[],
    ordering: string,
    xls = true,
  ) {
    const exportColumns: string[] = ['name', ...columns]
    const queryString = this.parseQueryString(params)

    let url = `${this.BACKEND_ADDRESS}samples/genomes/${queryString}`
    url += `&columns=${exportColumns.join(',')}`
    url += `&ordering=${ordering}`
    url += `&csv_stream=true`

    const response = await axios.get(url, {
      responseType: 'stream',
      adapter: 'fetch',
    })
    const stream = response.data
    if (xls) {
      const reader: ReadableStreamDefaultReader<string> = stream
        .pipeThrough(new TextDecoderStream())
        .getReader()
      this.saveAsXLSX(reader, exportColumns)
      return
    }
    const chunks = []

    chunks.push(exportColumns.join(';') + '\n') // add column names for csv export

    const outStream = new WritableStream({
      write(chunk) {
        chunks.push(chunk)
      },
      close() {
        // console.log('Stream closed')
      },
    })
    await stream.pipeThrough(new TextDecoderStream()).pipeTo(outStream)
    const arrayBuffer = await new Blob(chunks).arrayBuffer()
    const blob = new Blob([arrayBuffer])
    saveAs(blob, 'export.csv')
  }

  async saveAsXLSX(reader: ReadableStreamDefaultReader<string>, columns: string[]) {
    const workbook = new ExcelJS.Workbook()
    const worksheet = workbook.addWorksheet('Sheet 1')
    worksheet.columns = columns.map((c) => ({ header: c, key: c, width: 20 }))
    let data = '' as string
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      data += value
      if (data && data.includes('\n')) {
        const lines = data.split('\n')
        data = lines.pop() || ''
        for (const line of lines) {
          const values = line.split(';')
          const rowValues: { [key: string]: string | undefined } = {}
          columns.forEach((c, i) => {
            rowValues[c] = values[i]
          })
          worksheet.addRow(rowValues)
        }
      }
    }
    const buffer = await workbook.xlsx.writeBuffer()
    saveAs(
      new Blob([buffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      }),
      'export.xlsx',
    )
  }

  getSampleGenomePropertyOptions() {
    return this.getRequest(`properties/distinct_property_names/`, {}, false)
  }

  getSampleGenomePropertyOptionsAndTypes() {
    return this.getRequest(`properties/get_all_properties/`, {}, false)
  }

  getSampleStatistics(reference?: string) {
    const params = reference ? { reference } : {}
    return this.getRequest(`samples/statistics/`, params, false)
  }

  getSampleGenomePropertyValueOptions(propertyName: string, reference?: string) {
    // get unique value of each property_name
    const params = reference ? { reference } : {}
    return this.getRequest(
      `properties/distinct_properties/?property_name=${propertyName}`,
      params,
      false,
    )
  }
  getRepliconAccessionOptions(reference?: string) {
    const params = reference ? { reference } : {}
    return this.getRequest('replicons/distinct_accessions/', params, false)
  }
  getLineageOptions(reference?: string) {
    const params = reference ? { reference } : {}
    return this.getRequest(`samples/distinct_lineages/`, params, false)
  }
  getGeneSymbolOptions(reference?: string) {
    const params = reference ? { reference } : {}
    return this.getRequest(`genes/distinct_gene_symbols/`, params, false)
  }
  parseQueryString(query: FilterGroupRoot) {
    // remove properties (e.g. empty date ranges) with no value
    query.filters.andFilter = query.filters.andFilter.filter((filter) => {
      return !(filter.value === '')
    })
    if (Object.keys(query).length > 0) {
      return (
        '?' +
        Object.keys(query)
          .map(function (k) {
            const key = k as keyof FilterGroupRoot
            let value = JSON.stringify(query[key])
            if (value === undefined || value === null) {
              value = query[key]?.toString() || ''
            }
            const param = encodeURIComponent(k.toString().trim()) + '=' + encodeURIComponent(value)
            return param
          })
          .join('&')
      )
    } else return ''
  }
  uniqueMutationCount() {
    return this.getRequest(`mutations/distinct_mutations_count/`, {}, false)
  }
}
