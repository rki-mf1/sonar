export enum DjangoFilterType {
    EXACT = "exact",
    IEXACT = "iexact",
    CONTAINS = "contains",
    ICONTAINS = "icontains",
    IN = "in",
    GT = "gt",
    GTE = "gte",
    LT = "lt",
    LTE = "lte",
    STARTSWITH = "startswith",
    ISTARTSWITH = "istartswith",
    ENDSWITH = "endswith",
    IENDSWITH = "iendswith",
    RANGE = "range",
    ISNULL = "isnull",
    REGEX = "regex",
    IREGEX = "iregex",
}

export type PropertyFilter = {
    fetchOptions: boolean;
    label: string;
    value: string;
    propertyName: string;
    filterType: DjangoFilterType | null;
}
export type SNPProfileNtFilter = {
    label: string,
    geneSymbol: string,
    refNuc: string,
    refPos: string,
    altNuc: string
    exclude: boolean
}
export type SNPProfileAAFilter = {
    label: string,
    proteinSymbol: string,
    refAA: string,
    refPos: string,
    altAA: string,
    exclude: boolean
}
export type DelProfileNtFilter = {
    label: string,
    geneSymbol: string,
    firstDeletedNt: string,
    lastDeletedNt: string,
    exclude: boolean
}
export type DelProfileAAFilter = {
    label: string,
    proteinSymbol: string,
    firstDeletedAA: string,
    lastDeletedAA: string,
    exclude: boolean
}
export type InsProfileNtFilter = {
    label: string,
    geneSymbol: string,
    refNuc: string,
    refPos: string,
    altNucs: string,
    exclude: boolean
}
export type InsProfileAAFilter = {
    label: string,
    proteinSymbol: string,
    refAA: string,
    refPos: string,
    altAAs: string,
    exclude: boolean
}

export type ClassicFilter = {
    label: string,
    value: string,
    exclude: boolean
}

export type ProfileFilter =
    | ClassicFilter
    | SNPProfileNtFilter
    | SNPProfileAAFilter
    | DelProfileNtFilter
    | DelProfileAAFilter
    | InsProfileNtFilter
    | InsProfileAAFilter

export type GenomeFilter =
    | PropertyFilter
    | ProfileFilter

export type FilterGroupFilters = {
    andFilter: Record<string, string | number | boolean>[],
    orFilter: FilterGroupFilters[]
}

export type FilterGroupRoot = {
    limit?: number;
    offset?: number;
    filters: FilterGroupFilters;
}

export type AndFilters = {
    propertyFilters: PropertyFilter[];
    profileFilters: ProfileFilter[]
}

export type FilterGroup = {
    marked?: boolean;
    filterGroups: FilterGroup[];
    filters: AndFilters;
}
