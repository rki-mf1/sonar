import _csv
import ast
import csv
from dataclasses import dataclass
from datetime import datetime
import json
import os
import re
import time
import traceback
from typing import Generator

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.paginator import Paginator
from django.db.models import Exists
from django.db.models import F
from django.db.models import OuterRef
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Subquery
from django.http import StreamingHttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response

from covsonar_backend.settings import DEBUG
from covsonar_backend.settings import LOGGER
from covsonar_backend.settings import SONAR_DATA_ENTRY_FOLDER
from rest_api.data_entry.sample_job import delete_samples
from rest_api.data_entry.sample_job import delete_sequences
from rest_api.serializers import SampleGenomesExportStreamSerializer
from rest_api.utils import define_profile
from rest_api.utils import get_distinct_cds_accessions
from rest_api.utils import get_distinct_gene_symbols
from rest_api.utils import get_distinct_replicon_accessions
from rest_api.utils import resolve_ambiguous_NT_AA
from rest_api.utils import strtobool
from rest_api.viewsets import PropertyViewSet
from . import models
from .serializers import SampleGenomesSerializer
from .serializers import SampleGenomesSerializerVCF
from .serializers import SampleSerializer


@dataclass
class LineageInfo:
    name: str
    parent: str

    def __hash__(self):
        return hash((self.name, self.parent))


class Echo:
    def write(self, value):
        return value


class SampleFilterMixin:
    # Cache for gene symbols, replicons and CDS accessions
    _cached_gene_symbols = None
    _cached_replicons = None
    _cache_timestamp = None
    _cached_cds_accs = None
    CACHE_TTL = 3600 * 24  # 1 day

    @property
    def filter_label_to_methods(self):
        return {
            "Property": self.filter_property,
            "SNP Nt": self.filter_snp_profile_nt,
            "SNP AA": self.filter_snp_profile_aa,
            "Del Nt": self.filter_del_profile_nt,
            "Del AA": self.filter_del_profile_aa,
            "Ins Nt": self.filter_ins_profile_nt,
            "Ins AA": self.filter_ins_profile_aa,
            "Replicon": self.filter_replicon,
            "Reference": self.filter_reference,
            "Sample": self.filter_sample,
            "Lineages": self.filter_sublineages,
            "Annotation": self.filter_annotation,
            "DNA/AA Profile": self.filter_label,
        }

    @classmethod
    def get_gene_symbols(cls, force_refresh=False):
        """
        update cached gene symbol set if cache older than CACHE_TTL
        """
        now = time.time()
        if (
            force_refresh
            or cls._cached_gene_symbols is None
            or cls._cache_timestamp is None
            or (now - cls._cache_timestamp) > cls.CACHE_TTL
        ):

            symbols = get_distinct_gene_symbols()
            cls._cached_gene_symbols = set(symbols)

        return cls._cached_gene_symbols

    @classmethod
    def get_replicons(cls, reference_accession=None, force_refresh=True):
        """
        update cached replicon accession set if cache older than CACHE_TTL
        """
        now = time.time()
        if (
            force_refresh
            or cls._cached_replicons is None
            or cls._cache_timestamp is None
            or (now - cls._cache_timestamp) > cls.CACHE_TTL
        ):

            replicons_list = get_distinct_replicon_accessions(reference_accession)
            cls._cached_replicons = set(replicons_list)
            cls._cache_timestamp = now

        return cls._cached_replicons

    @classmethod
    def get_cds_accessions(cls, replicon=None, force_refresh=True):
        now = time.time()
        if (
            force_refresh
            or cls._cached_replicons is None
            or cls._cache_timestamp is None
            or (now - cls._cache_timestamp) > cls.CACHE_TTL
        ):
            cds_acc = get_distinct_cds_accessions(replicon=replicon)
            cls._cached_cds_accs = set(cds_acc)
        return cls._cached_cds_accs

    def _get_reference_replicon_count(self, reference_accession):
        """
        Returns the number of replicons for a given reference.
        Returns None if reference not found.
        """
        return models.Replicon.objects.filter(
            reference__accession=reference_accession
        ).count()

    def _resolve_replicon_for_query(self, parsed_mutation, reference_accession):
        """
        Determines which replicon to use for mutation query.

        Returns:
            - replicon_accession (str) if successful
            - Raises ValueError if ambiguous (multiple replicons without explicit accession)
        """
        # case 1: replicon accession in parsed mutation
        if (
            "replicon_accession" in parsed_mutation
            and parsed_mutation["replicon_accession"]
        ):
            return parsed_mutation["replicon_accession"]

        # case 2: no replicon accession in parsed mutation
        replicon_count = self._get_reference_replicon_count(reference_accession)
        LOGGER.debug(
            f"replicon_count in resolve replicon fore reference {reference_accession}: {replicon_count}"
        )

        if replicon_count is None or replicon_count == 0:
            raise ValueError(f"No replicons found for reference {reference_accession}.")

        if replicon_count == 1:
            # one replicon: use this replicon
            replicon = models.Replicon.objects.get(
                reference__accession=reference_accession
            )
            return replicon.accession

        # case 3: multiple replicons per reference, parsed mutation without replicon accession
        if replicon_count > 1:
            raise ValueError(
                f"Reference {reference_accession} has {replicon_count} replicons. "
                f"Please specify replicon accession (e.g., NC_026438.1:A425G)."
            )

    def resolve_recursive_genome_filter(
        self, filters, reference_accession=None, depth=0
    ) -> Q:
        indent = "  " * depth
        LOGGER.debug(f"{indent}resolve_genome_filter called, depth={depth}")
        LOGGER.debug(f"{indent}filters: {filters}")
        LOGGER.debug(f"{indent}reference_accession: {reference_accession}")
        q_obj = Q()
        # Process single filter at current level
        if "label" in filters:
            q_obj &= self.eval_basic_filter(filters, reference_accession)

        # Process AND filters
        for f in filters.get("andFilter", []):
            if "orFilter" in f or "andFilter" in f:
                # Recursive call for nested filters
                q_obj &= self.resolve_recursive_genome_filter(
                    f, reference_accession, depth + 1
                )
            else:
                q_obj &= self.eval_basic_filter(f, reference_accession)

        # Process OR filters
        for or_filter in filters.get("orFilter", []):
            q_obj |= self.resolve_recursive_genome_filter(
                or_filter, reference_accession, depth + 1
            )
        return q_obj

    def eval_basic_filter(self, filter_dict, reference_accession) -> Q:
        """
        Evaluate a single basic filter.
        """
        label = filter_dict.get("label")
        method = self.filter_label_to_methods.get(label)
        if not method:
            raise Exception(f"Filter method not found for: {label}")
        # Pass reference_accession to filter methods
        filter_kwargs = {**filter_dict, "reference_accession": reference_accession}

        return method(**filter_kwargs)

    def get_filtered_queryset(self, request: Request):
        """
        retrieve filtered queryset Sample based on request parameters
        """
        if not (filter_params := request.query_params.get("filters")):
            queryset = models.Sample.objects.all()
        else:
            filters = json.loads(filter_params)
            if "reference" in request.query_params:
                reference_accession = (
                    request.query_params.get("reference").strip('"').strip()
                )
            else:
                reference_accession = filters.get("reference")
            if not reference_accession:
                raise ValueError("Reference accession is required in filters.")

            LOGGER.info(
                f"Genomes Query, conditions: {filters}, reference: {reference_accession}"
            )

            q_filter = self.resolve_recursive_genome_filter(
                filters, reference_accession
            )

            queryset = models.Sample.objects.filter(
                q_filter,
                sequences__alignments__replicon__reference__accession=reference_accession,
            ).distinct()

        queryset = queryset.select_related().prefetch_related(
            "sequences",
            "properties__property",
        )

        return queryset

    def filter_label(
        self,
        value,
        reference_accession=None,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        final_query = Q()
        # Split the input value by either commas, semicolom, whitespace, or combinations of these,
        # remove seperators from string end
        mutations = re.split(r"[,\s;]+", value.strip(",; \t\r\n"))
        for mutation in mutations:
            parsed_mutation = define_profile(
                mutation, self.get_gene_symbols(), self.get_replicons()
            )
            # resolve replicon accession
            if parsed_mutation["label"] in ["SNP Nt", "Ins Nt", "Del Nt"]:
                replicon_accession = self._resolve_replicon_for_query(
                    parsed_mutation, reference_accession
                )
                parsed_mutation["replicon_accession"] = replicon_accession
            # Validate protein name for AA mutations
            if (
                "protein_symbol" in parsed_mutation
                and parsed_mutation["protein_symbol"] not in self.get_gene_symbols()
            ):
                raise ValueError(
                    f"Invalid protein name: {parsed_mutation['protein_symbol']}."
                )
            # Check the parsed mutation type and call appropriate filter function
            if parsed_mutation.get("label") == "SNP Nt":
                q_obj = self.filter_snp_profile_nt(
                    ref_nuc=parsed_mutation["ref_nuc"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_nuc=parsed_mutation["alt_nuc"],
                    replicon_accession=parsed_mutation["replicon_accession"],
                )

            elif parsed_mutation.get("label") == "SNP AA":
                q_obj = self.filter_snp_profile_aa(
                    protein_symbol=parsed_mutation["protein_symbol"],
                    ref_aa=parsed_mutation["ref_aa"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_aa=parsed_mutation["alt_aa"],
                )

            elif parsed_mutation.get("label") == "Del Nt":
                q_obj = self.filter_del_profile_nt(
                    first_deleted=parsed_mutation["first_deleted"],
                    last_deleted=parsed_mutation.get("last_deleted", ""),
                    replicon_accession=parsed_mutation["replicon_accession"],
                )

            elif parsed_mutation.get("label") == "Del AA":
                q_obj = self.filter_del_profile_aa(
                    protein_symbol=parsed_mutation["protein_symbol"],
                    first_deleted=parsed_mutation["first_deleted"],
                    last_deleted=parsed_mutation.get("last_deleted", ""),
                )

            elif parsed_mutation.get("label") == "Ins Nt":
                q_obj = self.filter_ins_profile_nt(
                    ref_nuc=parsed_mutation["ref_nuc"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_nuc=parsed_mutation["alt_nuc"],
                    replicon_accession=parsed_mutation["replicon_accession"],
                )

            elif parsed_mutation.get("label") == "Ins AA":
                q_obj = self.filter_ins_profile_aa(
                    protein_symbol=parsed_mutation["protein_symbol"],
                    ref_aa=parsed_mutation["ref_aa"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_aa=parsed_mutation["alt_aa"],
                )

            else:

                raise ValueError(
                    f"Unsupported mutation type: {parsed_mutation.get('label')}"
                )
            # Combine queries with AND operator (&) for each mutation
            final_query &= q_obj

        if exclude:
            final_query = ~final_query

        return final_query

    def filter_annotation(
        self,
        property_name,
        filter_type,
        value,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        query = {}
        query[f"nucleotide_mutations__annotations__{property_name}__{filter_type}"] = (
            value
        )

        alignment_qs = models.Alignment.objects.filter(**query)
        filters = {"sequences__alignments__in": alignment_qs}

        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_property(
        self,
        property_name,
        filter_type,
        value,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # Convert str of list into list object
        # "['X','N']" -> ['X','N']
        if isinstance(value, str):
            try:
                # Safely evaluate the string representation of the list and convert it to a list object
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                # Handle the case where the string couldn't be evaluated as a list
                pass

        # check the filter_type
        if filter_type == "contains":
            value = value.strip("%")
        elif filter_type == "range":
            if isinstance(value, str):
                value = value.split(",")

        self.has_property_filter = True

        # Special handling for 'length' - stored in Sequence table
        if property_name == "length":
            query = {}
            query[f"sequences__{property_name}__{filter_type}"] = value
        elif property_name in [
            field.name for field in models.Sample._meta.get_fields()
        ]:
            query = {}
            query[f"{property_name}__{filter_type}"] = value
        else:
            datatype = models.Property.objects.get(name=property_name).datatype
            query = {f"properties__property__name": property_name}
            query[f"properties__{datatype}__{filter_type}"] = value
        if exclude:
            return ~Q(**query)
        return Q(**query)

    def filter_nt_mutations(
        self,
        mutation_condition,
        exclude: bool = False,
        replicon_accession: str = None,
    ):
        if replicon_accession:
            mutation_condition &= Q(replicon__accession=replicon_accession)

        # Use EXISTS subquery instead of JOIN
        mutation_subquery = models.NucleotideMutation.objects.filter(
            mutation_condition, alignments__sequence__samples=OuterRef("pk")
        )

        if exclude:
            return Q(
                pk__in=models.Sample.objects.exclude(
                    pk__in=models.Sample.objects.filter(Exists(mutation_subquery))
                )
            )

        return Q(Exists(mutation_subquery))

    def filter_aa_mutations(
        self,
        mutation_condition,
        exclude: bool = False,
        replicon_accession: str = None,
    ):
        if replicon_accession:
            mutation_condition &= Q(replicon__accession=replicon_accession)

        # Use EXISTS subquery instead of JOIN
        mutation_subquery = models.AminoAcidMutation.objects.filter(
            mutation_condition, alignments__sequence__samples=OuterRef("pk")
        )

        if exclude:
            return Q(
                pk__in=models.Sample.objects.exclude(
                    pk__in=models.Sample.objects.filter(Exists(mutation_subquery))
                )
            )

        return Q(Exists(mutation_subquery))

    def filter_snp_profile_nt(
        self,
        # gene_symbol: str,
        ref_nuc: str,
        ref_pos: int,
        alt_nuc: str,
        replicon_accession: str = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For NT: ref_nuc followed by ref_pos followed by alt_nuc (e.g. T28175C).
        if alt_nuc == "N":
            mutation_alt = Q()
            for x in resolve_ambiguous_NT_AA(type="nt", char=alt_nuc):
                mutation_alt |= Q(alt=x)
        else:
            mutation_alt = Q(alt=alt_nuc if alt_nuc != "n" else "N")

        mutation_condition = Q(end=ref_pos) & Q(ref=ref_nuc) & mutation_alt

        return self.filter_nt_mutations(mutation_condition, exclude, replicon_accession)

    def filter_snp_profile_aa(
        self,
        protein_symbol: str,
        ref_aa: str,
        ref_pos: str,
        alt_aa: str,
        replicon_accession: str = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For AA: protein_symbol:ref_aa followed by ref_pos followed by alt_aa (e.g. OPG098:E162K)
        if protein_symbol not in self.get_gene_symbols():
            raise ValueError(f"Invalid protein name: {protein_symbol}.")
        if alt_aa == "X":
            mutation_alt = Q()
            for x in resolve_ambiguous_NT_AA(type="aa", char=alt_aa):
                mutation_alt | Q(alt=x)
        else:
            mutation_alt = Q(alt=alt_aa if alt_aa != "x" else "X")

        mutation_condition = (
            Q(end=ref_pos)
            & Q(ref=ref_aa)
            & (mutation_alt)
            & Q(cds__gene__symbol=protein_symbol)
        )
        return self.filter_aa_mutations(mutation_condition, exclude, replicon_accession)

    def filter_del_profile_nt(
        self,
        first_deleted: str,
        last_deleted: str,
        replicon_accession: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For NT: del:first_NT_deleted-last_NT_deleted (e.g. del:133177-133186).
        # in case only single deltion bp
        if last_deleted == "":
            last_deleted = first_deleted

        mutation_condition = (
            Q(start=int(first_deleted) - 1) & Q(end=int(last_deleted)) & Q(alt="")
        )
        return self.filter_nt_mutations(mutation_condition, exclude, replicon_accession)

    def filter_del_profile_aa(
        self,
        protein_symbol: str,
        first_deleted: str,
        last_deleted: str,
        replicon_accession: str = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For AA: protein_symbol:del:first_AA_deleted-last_AA_deleted (e.g. OPG197:del:34-35)
        if protein_symbol not in self.get_gene_symbols():
            raise ValueError(f"Invalid protein name: {protein_symbol}.")
        # in case only single deltion bp
        if last_deleted == "":
            last_deleted = first_deleted

        mutation_condition = (
            Q(cds__gene__symbol__iexact=protein_symbol)
            & Q(start=int(first_deleted) - 1)
            & Q(end=int(last_deleted))
            & Q(alt="")
        )

        return self.filter_aa_mutations(mutation_condition, exclude, replicon_accession)

    def filter_ins_profile_nt(
        self,
        ref_nuc: str,
        ref_pos: int,
        alt_nuc: str,
        replicon_accession: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For NT: ref_nuc followed by ref_pos followed by alt_nucs (e.g. T133102TTT)
        mutation_condition = Q(end=ref_pos) & Q(ref=ref_nuc) & Q(alt=alt_nuc)
        return self.filter_nt_mutations(mutation_condition, exclude, replicon_accession)

    def filter_ins_profile_aa(
        self,
        protein_symbol: str,
        ref_aa: str,
        ref_pos: int,
        alt_aa: str,
        replicon_accession: str = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For AA: protein_symbol:ref_aa followed by ref_pos followed by alt_aas (e.g. OPG197:A34AK)
        if protein_symbol not in self.get_gene_symbols():
            raise ValueError(f"Invalid protein name: {protein_symbol}.")
        mutation_condition = (
            Q(end=ref_pos)
            & Q(ref=ref_aa)
            & Q(alt=alt_aa)
            & Q(cds__gene__symbol=protein_symbol)
        )

        return self.filter_aa_mutations(mutation_condition, exclude, replicon_accession)

    def filter_sample(
        self,
        value: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        if isinstance(value, str):
            sample_list = ast.literal_eval(value)
        else:
            sample_list = value

        if exclude:
            return ~Q(name__in=sample_list)
        else:
            return Q(name__in=sample_list)

    def filter_replicon(
        self,
        replicon_accession,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        if exclude:
            return ~Q(sequences__alignments__replicon__accession=replicon_accession)
        else:
            return Q(sequences__alignments__replicon__accession=replicon_accession)

    def filter_reference(
        self,
        accession,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        if exclude:
            return ~Q(sequences__alignments__replicon__reference__accession=accession)
        else:
            return Q(sequences__alignments__replicon__reference__accession=accession)

    def filter_sublineages(
        self,
        lineageList,
        exclude: bool = False,
        includeSublineages: bool = True,
        *args,
        **kwargs,
    ):
        if isinstance(lineageList, str):
            lineageList = [lineageList]  # convert to list if a single string is passed

        lineages = models.Lineage.objects.filter(name__in=lineageList)

        if not lineages.exists():
            raise Exception(f"Lineage {lineages} not found.")
        if includeSublineages:
            sublineages = []
            for l in lineages:
                sublineages.extend(l.get_sublineages())
        else:
            sublineages = list(lineages)

        # match for all sublineages of all given lineages
        return self.filter_property(
            "lineage",
            "in",
            sublineages,
            exclude,
        )


class SampleViewSet(
    SampleFilterMixin,
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Sample.objects.all().order_by("id")
    serializer_class = SampleSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    lookup_field = "name"
    filter_fields = ["name"]

    def _get_genomic_and_proteomic_profiles_queryset(
        self, queryset, reference_accession, showNX=False
    ):
        """
        Optimized prefetching for genomic and protemoic profiles
        """

        genomic_profiles_qs = models.NucleotideMutation.objects.only(
            "ref", "alt", "start", "end", "is_frameshift", "replicon_id"
        ).prefetch_related(
            "annotations"
        )  # Prefetch annotations direkt
        if not showNX:
            genomic_profiles_qs = genomic_profiles_qs.exclude(alt="N")
        genomic_profiles_qs = genomic_profiles_qs.order_by("start")

        proteomic_profiles_qs = models.AminoAcidMutation.objects.only(
            "ref", "alt", "start", "end", "cds_id"
        ).prefetch_related(
            "cds__gene", "cds__gene__replicon"  # Auch replicon prefetchen
        )
        if not showNX:
            proteomic_profiles_qs = proteomic_profiles_qs.exclude(alt="X")
        proteomic_profiles_qs = proteomic_profiles_qs.order_by("cds", "start")

        queryset = queryset.prefetch_related(
            "sequences__alignments__replicon__reference",
            Prefetch(
                "sequences__alignments__nucleotide_mutations",
                queryset=genomic_profiles_qs,
                to_attr="genomic_profiles",
            ),
            Prefetch(
                "sequences__alignments__amino_acid_mutations",
                queryset=proteomic_profiles_qs,
                to_attr="proteomic_profiles",
            ),
        )

        return queryset

    # actions
    @action(detail=False, methods=["get"])
    def genomes(self, request: Request, *args, **kwargs):
        """
        fetch proteomic and genomic profiles based on provided filters and optional parameters
        """
        try:
            timer = datetime.now()
            showNX = strtobool(request.query_params.get("showNX", "False"))
            csv_stream = strtobool(request.query_params.get("csv_stream", "False"))
            vcf_format = strtobool(request.query_params.get("vcf_format", "False"))

            LOGGER.info(
                f"Genomes Query, optional parameters: showNX:{showNX} csv_stream:{csv_stream}"
            )

            self.has_property_filter = False

            queryset = self.get_filtered_queryset(request)

            # apply ID ('name') filter if provided
            if name_filter := request.query_params.get("name"):
                queryset = queryset.filter(name=name_filter)

            # Get reference_accession für profil-prefetching
            filter_params = request.query_params.get("filters")
            if filter_params:
                filters = json.loads(filter_params)
                reference_accession = filters.get("reference")
            else:
                reference_accession = (
                    request.query_params.get("reference", "").strip('"').strip()
                )

            # Optimized prefetching
            queryset = self._get_genomic_and_proteomic_profiles_queryset(
                queryset, reference_accession, showNX
            )

            if DEBUG:
                LOGGER.info(f"Query: {queryset.query}")

            # apply ordering if specified
            ordering = request.query_params.get("ordering")
            if ordering:
                queryset = self._apply_ordering(queryset, ordering)
            else:
                queryset = queryset.order_by("-collection_date")

            # return csv stream if specified
            if csv_stream:
                return self._return_csv_stream(queryset, request, showNX)

            # return vcf format if specified
            if vcf_format:
                return self._return_vcf_format(queryset, showNX)

            # default response - paginate after prefetching
            queryset = self.paginate_queryset(queryset)
            LOGGER.info(
                f"Query time done in {datetime.now() - timer}, Start to Format result"
            )

            serializer = SampleGenomesSerializer(
                queryset, many=True, context={"request": request, "showNX": showNX}
            )
            timer = datetime.now()
            LOGGER.info(
                f"Serializer done in {datetime.now() - timer}, Start to Format result"
            )
            return self.get_paginated_response(serializer.data)

        except ValueError as e:
            return Response(data={"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response(
                data={"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _apply_ordering(self, queryset, ordering):
        """
        apply given ordering to queryset
        """
        property_names = PropertyViewSet.get_custom_property_names()
        ordering_col_name = ordering.lstrip("-")
        reverse_order = ordering.startswith("-")

        if ordering_col_name in property_names:
            datatype = models.Property.objects.get(name=ordering_col_name).datatype
            queryset = queryset.order_by(
                Subquery(
                    models.Sample2Property.objects.filter(
                        property__name=ordering_col_name, sample=OuterRef("id")
                    ).values(datatype)
                )
            )
            if reverse_order:
                queryset = queryset.reverse()
        else:
            queryset = queryset.order_by(ordering)

        return queryset

    def _get_genomic_and_proteomic_profile_columns(self, columns, reference_accession):
        """
        Expand genomic_profiles and proteomic_profiles columns into individual columns
        based on existing gene symbols and replicon accessions.
        """
        expanded_columns = []
        for column in columns:
            if column == "genomic_profiles":
                replicons = self.get_replicons(reference_accession)
                for replicon in sorted(list(replicons)):
                    expanded_columns.append(f"genomic_profile: {replicon}")
            elif column == "proteomic_profiles":
                replicons = self.get_replicons(reference_accession)
                for replicon in sorted(list(replicons)):
                    for cds_acc in sorted(list(self.get_cds_accessions(replicon))):
                        expanded_columns.append(
                            f"proteomic_profile: {replicon}: {cds_acc}"
                        )
            else:
                expanded_columns.append(column)
        return expanded_columns

    def _return_csv_stream(self, queryset, request, showNX=False):
        """
        stream queryset data as a csv file
        """
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer, delimiter=";")
        columns = request.query_params.get("columns")
        reference_accession = request.query_params.get("reference")
        reference_accession = (
            reference_accession.strip('"').strip("'") if reference_accession else None
        )

        if not columns:
            raise Exception("No columns provided")

        columns = columns.split(",")
        columns = self._get_genomic_and_proteomic_profile_columns(
            columns, reference_accession
        )
        filename = request.query_params.get("filename", "sample_genomes.csv")

        return StreamingHttpResponse(
            self._stream_serialized_data(queryset, columns, writer, showNX),
            content_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def _return_vcf_format(self, queryset, showNX=False):
        """
        return queryset data in vcf format
        """
        queryset = self.paginate_queryset(queryset)
        serializer = SampleGenomesSerializerVCF(
            queryset, many=True, context={"request": self.request, "showNX": showNX}
        )
        return self.get_paginated_response(serializer.data)

    def _stream_serialized_data(
        self,
        queryset: QuerySet,
        columns: list[str],
        writer: "_csv._writer",
        showNX: bool = False,
    ) -> Generator:
        serializer = SampleGenomesExportStreamSerializer

        serializer.columns = columns
        yield writer.writerow(columns)
        paginator = Paginator(queryset, 100)
        for page in paginator.page_range:
            for serialized in serializer(
                paginator.page(page).object_list,
                many=True,
                context={"showNX": showNX, "columns": columns},
            ).data:
                yield writer.writerow(serialized["row"])

    def _temp_save_file(self, uploaded_file: InMemoryUploadedFile):
        file_path = os.path.join(SONAR_DATA_ENTRY_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        return file_path

    @action(detail=False, methods=["get"])
    def get_sequence_data(self, request: Request, *args, **kwargs):
        sequence_name = request.GET.get("sequence_name", "")
        if not sequence_name:
            return Response(
                {"detail": "Sequence name is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sequence = (
            models.Sequence.objects.filter(name=sequence_name)
            .annotate(
                sequence_id=F("id"),
                sequence_seqhash=F("seqhash"),
            )
            .values("sequence_id", "name", "sequence_seqhash")
        )
        if sequence:
            sequence_data = list(sequence)[0]
        else:
            print("Cannot find:", sequence_name)
            sequence_data = {}

        return Response(data=sequence_data)

    @action(detail=False, methods=["post"])
    def get_bulk_sequence_data(self, request: Request, *args, **kwargs):
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body.decode("utf-8"))
            # example to be parsed data: {"sequence_data": ["IMS-SEQ-01", "IMS-SEQ-04", "value3"]}
            sequence_data_list = data.get("sequence_data", [])

            sequence_model = (
                models.Sequence.objects.filter(name__in=sequence_data_list)
                .annotate(
                    sequence_id=F("id"),
                    sequence_seqhash=F("seqhash"),
                )
                .values("sequence_id", "name", "sequence_seqhash")
            )
            # Convert the QuerySet to a list of dictionaries
            sequence_data = list(sequence_model)

            # Check for missing samples and add them to the result
            missing_samples = set(sequence_data_list) - set(
                item["name"] for item in sequence_data
            )
            for missing_sample in missing_samples:
                sequence_data.append(
                    {
                        "sequence_id": None,
                        "name": missing_sample,
                        "sequence_seqhash": None,
                    }
                )
            return Response(sequence_data, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid JSON data / structure"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def delete_sample_data(self, request: Request, *args, **kwargs):
        sample_data = {}
        reference_accession = request.data.get("reference", "")
        sample_list = json.loads(request.data.get("sample_list"))
        if DEBUG:
            print("Reference Accession:", reference_accession)
            print("Sample List:", sample_list)

        sample_data = delete_samples(sample_list=sample_list)

        return Response(data=sample_data)

    @action(detail=False, methods=["post"])
    def delete_sequence_data(self, request: Request, *args, **kwargs):
        sequence_data = {}
        reference_accession = request.data.get("reference", "")
        sequence_list = json.loads(request.data.get("sequence_list"))
        if DEBUG:
            print("Reference Accession:", reference_accession)
            print("Sequence List:", sequence_list)

        sequence_data = delete_sequences(sequence_list=sequence_list)

        return Response(data=sequence_data)


class SampleGenomeViewSet(viewsets.GenericViewSet, generics.mixins.ListModelMixin):
    queryset = models.Sample.objects.all()
    serializer_class = SampleGenomesSerializer

    @action(detail=False, methods=["get"])
    def match(self, request: Request, *args, **kwargs):
        profile_filters = request.query_params.getlist("profile_filters")
        param_filters = request.query_params.getlist("param_filters")
