import datetime
import re
import sys
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from urllib.parse import urlparse

import pandas as pd
from sonar_cli.config import SUPPORTED_DB_VERSION
import sqlparse

from .logging import LoggingConfigurator

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class sonarDBManager:
    """
    A class to handle genomic data stored in database.
    """

    # CONSTANTS

    OPERATORS = {
        "standard": {
            "=": "=",
            ">": ">",
            "<": "<",
            ">=": ">=",
            "<=": "<=",
            "IN": "IN",
            "LIKE": "LIKE",
            "BETWEEN": "BETWEEN",
        },
        "inverse": {
            "=": "!=",
            ">": "<=",
            "<": ">=",
            ">=": "<",
            "<=": ">",
            "IN": "NOT IN",
            "LIKE": "NOT LIKE",
            "BETWEEN": "NOT BETWEEN",
        },
        "default": "=",
    }

    IUPAC_CODES = {
        "nt": {
            "A": set("A"),
            "C": set("C"),
            "G": set("G"),
            "T": set("T"),
            "R": set("AGR"),
            "Y": set("CTY"),
            "S": set("GCS"),
            "W": set("ATW"),
            "K": set("GTK"),
            "M": set("ACM"),
            "B": set("CGTB"),
            "D": set("AGTD"),
            "H": set("ACTH"),
            "V": set("ACGV"),
            "N": set("ACGTRYSWKMBDHVN"),
            "n": set("N"),
        },
        "aa": {
            "A": set("A"),
            "R": set("R"),
            "N": set("N"),
            "D": set("D"),
            "C": set("C"),
            "Q": set("Q"),
            "E": set("E"),
            "G": set("G"),
            "H": set("H"),
            "I": set("I"),
            "L": set("L"),
            "K": set("K"),
            "M": set("M"),
            "F": set("F"),
            "P": set("P"),
            "S": set("S"),
            "T": set("T"),
            "W": set("W"),
            "Y": set("Y"),
            "V": set("V"),
            "U": set("U"),
            "O": set("O"),
            "B": set("DNB"),
            "Z": set("EQZ"),
            "J": set("ILJ"),
            "Φ": set("VILFWYMΦ"),
            "Ω": set("FWYHΩ"),
            "Ψ": set("VILMΨ"),
            "π": set("PGASπ"),
            "ζ": set("STHNQEDKRζ"),
            "+": set("KRH+"),
            "-": set("DE-"),
            "X": set("ARNDCQEGHILKMFPSTWYVUOBZJΦΩΨπζ+-X"),
            "x": set("X"),
        },
    }

    def __init__(self, db: str, readonly: bool = True, debug: bool = False) -> None:

        if db is not None:
            self.db_url = db
        else:
            LOGGER.error("NO database info. is given.")
            sys.exit(1)

        self.con = None
        self.cursor = None
        self.__mode = "ro" if readonly else "rwc"
        self.__uri = urlparse(self.db_url)
        self.db_user = self.__uri.username
        self.db_pass = self.__uri.password
        self.db_url = self.__uri.hostname
        self.db_port = self.__uri.port
        self.db_database = self.__uri.path.replace("/", "")
        self.__properties = {}
        self.__references = {}  # Keep all references that were in a database.
        self.__source_references_df = None
        self.__source_ref_dict = {}
        self.__illegal_properties = {
            "SAMPLE",
            "GENOMIC_PROFILE",
            "SAMPLE_NAME",
            "PROTEOMIC_PROFILE",
            "FRAMESHIFT_MUTATION",
        }

    def __enter__(self) -> "sonarDBManager":
        """
        Enter the runtime  related to the database object.

        Returns:
            DBOperations: The current instance.
        """
        #self.con = self.connect()
        #self.cursor = self.con.cursor(dictionary=True)
        #self.check_db_compatibility()
        #self.start_transaction()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Exit the runtime context and close the database connection.
        In case of raised errors, the database is rolled back.
        """
        if [exc_type, exc_value, exc_traceback].count(None) != 3:
            if self.__mode == "rwc":
                LOGGER.info("rollback database")
                self.rollback()
        elif self.__mode == "rwc":
            self.commit()
        self.close()

    def start_transaction(self):
        self.cursor.execute("START TRANSACTION;")

    def commit(self):
        """commit"""
        self.con.commit()

    def rollback(self):
        """roll back"""
        self.con.rollback()

    def close(self):
        """close database connection"""
        self.cursor.close()
        self.con.close()

    def check_db_compatibility(self) -> None:
        """
        Check the compatibility of the database.

        This method checks whether the version of the database is compatible with
        the software. It compares the current version of the database with the
        supported version defined in the SUPPORTED_DB_VERSION variable.

        Raises:
            SystemExit: If the database version is not identical to the supported version,
                        indicating that the software might be outdated or too new.
        """
        current_version = self.get_db_version()
        if not current_version == SUPPORTED_DB_VERSION:
            LOGGER.error(
                "The given database is not compatible with this version of sonar (database version: "
                + str(current_version)
                + "; supported database version: "
                + str(SUPPORTED_DB_VERSION)
                + ")"
            )
            sys.exit(1)

    def get_db_version(self) -> int:
        """
        Get the version number of the database.

        Returns:
            int: The version number of the database.
        """

        self.cursor.execute(f"SELECT `{self.db_database}`.DB_VERSION() AS version;")
        return self.cursor.fetchone()["version"]

    def format_sql(self, sql: str) -> str:
        """
        Formats the given SQL string.

        Args:
            sql (str): The raw SQL string.

        Returns:
            str: The formatted SQL string.
        """
        return sqlparse.format(sql, reindent=True, keyword_case="upper")

    @property
    def references(self):
        """
        Return all references.

        Returns:
            dict:
        """
        if self.__references == {}:
            sql = "SELECT `id`, `accession`, `description`, `organism` FROM reference;"
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            if rows:
                self.__references = rows
            else:
                self.__references = {}
        return self.__references

    @property
    def properties(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns property data as a dict of dict where key is property name.
        If data is not in the cache, it fetches data from the SQLite database.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary with property names as keys
            and corresponding property data as values.
        """
        if not self.__properties:
            sql = f"SELECT * FROM {self.db_database}.property;"
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            self.__properties = {} if not rows else {x["name"]: x for x in rows}
        return self.__properties

    @property
    def sequence_references(self):
        """
        Return all original ref. seqs.

        (i.e., only type that is equal to 'source'
        from element table.)
        id (elem_ID)  molecule_id    type    accession  ... strand                                           sequence  standard  parent_id
         1   1   source  NC_063383.1  ...      0  ATTTTACTATTTTATTTAGTGTCTAGAAAAAAATGTGTGACCCACG...         1          0
        Return
            dict:
                ref. sequence; {"1": "AAATTTT"}
        """
        if self.__source_ref_dict == {}:
            all_elem_dict = self.get_molecule_ids()
            _list = []
            for key, value in all_elem_dict.items():
                # get source seq. by molecule_id
                _data = self.get_source(molecule_id=value)

                #  pd.DataFrame.from_dict(dbm.get_elements(molecule_id = value))
                _list.append(_data)
            self.__source_references_df = pd.DataFrame(_list)
            self.__source_ref_dict = dict(
                zip(
                    self.__source_references_df.id, self.__source_references_df.sequence
                )
            )
        return self.__source_ref_dict

    def get_molecule_data(
        self, *fields, reference_accession: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dictionary with molecule accessions as keys and sub-dicts as values for all molecules
        of a given (or the default) reference. The sub-dicts store all table field names
        (or, alternatively, the given table field names only) as keys and the stored data as values.

        Args:
            *fields: Fields to be included in the sub-dicts.
            reference_accession (str, optional): The reference accession. Defaults to None, which means the default reference.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary with molecule accessions as keys and their data as values.

            Examples:
            {'NC_063383.1': {'molecule.accession': 'NC_063383.1', 'molecule.id': 1, 'molecule.standard': 1, 'translation.id': 1}}
        """
        if not fields:
            fields = "*"
        elif "`molecule.accession`" not in fields:
            fields = list(fields) + ["`molecule.accession`"]
        if reference_accession:
            condition = "`reference.accession` = ?"
            vals = [reference_accession]
        else:
            condition = "`reference.standard` = ?"
            vals = [1]
        sql = (
            "SELECT "
            + ", ".join(fields)
            + " FROM referenceView WHERE "
            + condition
            + ";"
        )
        self.cursor.execute(sql, vals)
        row = self.cursor.fetchall()
        if row:
            return {x["molecule.accession"]: x for x in row}
        return {}

    def get_source(self, molecule_id: int) -> Optional[str]:
        """
        Returns the source data given a molecule id.

        Args:
            molecule_id (int): The id of the molecule.

        Returns:
            Optional[str]: The source if it exists, None otherwise.

        Example usage:
        >>> dbm = getfixture('init_readonly_dbm')
        >>> dbm.get_source(molecule_id=5)
        >>> dbm.get_source(molecule_id=1)['accession']
        'MN908947.3'
        """
        # Get the source elements given a molecule id
        source_elements = self.get_elements(molecule_id, "source")

        # Return None if no source elements found, otherwise return the first source element
        return None if not source_elements else source_elements[0]

    def get_elements(self, molecule_id, *types):
        """
        Returns all elements based on given molecule id
        """
        sql = "SELECT * FROM element WHERE molecule_id = ?"
        if types:
            sql += " AND type IN (" + ", ".join(["?"] * len(types)) + ");"
        row = self.cursor.execute(sql, [molecule_id] + list(types))
        row = self.cursor.fetchall()
        if not row:
            return []
        return row

    def get_sample_data(self, sample_name: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Returns a tuple of rowid and seqhash of a sample based on its name if it exists, else a tuple of Nones is returned.

        Args:
            sample_name (str): Name of the sample.

        Returns:
            Optional[Tuple[int,str]]: Tuple of id and seqhash of the sample, if exists, else a Tuple of None, None.

        """
        sql = "SELECT id, seqhash FROM sample WHERE name = ? LIMIT 1;"
        self.cursor.execute(sql, [sample_name])
        row = self.cursor.fetchone()
        return (row["id"], row["seqhash"]) if row else (None, None)

    def get_alignment_id(self, seqhash: str, element_id: int) -> Optional[int]:
        """
        Returns the rowid of a sample based on the respective seqhash and element. If no
        alignment of the given sequence to the given element has been stored, None is returned.

        Args:
            seqhash (str): The seqhash of the sample.
            element_id (int): The element id.

        Returns:
            Optional[int]: The id of the alignment if exists, else None.

        """
        sql = "SELECT id FROM alignment WHERE element_id = ? AND seqhash = ? LIMIT 1;"
        self.cursor.execute(sql, [element_id, seqhash])
        row = self.cursor.fetchone()
        return None if row is None else row["id"]

    def get_variant_id(
        self, element_id: int, start: int, end: int, ref: str, alt: str
    ) -> Optional[int]:
        """
        Retrieves the ID of the variant based on the given parameters.

        Args:
            element_id (int): ID of the element.
            start (int): Start position of the variant.
            end (int): End position of the variant.
            ref (str): Reference base(s).
            alt (str): Alternative base(s).

        Returns:
            int or None: ID of the variant if found, else None.
        """
        # Construct SQL query to fetch the variant ID
        sql = "SELECT id FROM variant WHERE element_id = ? AND start = ? AND end = ? AND ref = ? AND alt = ?;"

        # Execute the query and fetch the result
        self.cursor.execute(sql, [element_id, start, end, ref, alt])
        row = self.cursor.fetchone()
        # Return the variant ID if found, else None
        return None if row is None else row["id"]

    def get_variant_ids(self, variant_data_list):
        """
        Retrieves the ID of the variant based on the given list of variant.
        [ (element_id, ref, alt, start, end )]

        """

        if not variant_data_list:
            return []

        placeholders = ",".join(["(?, ?, ?, ?, ?)"] * len(variant_data_list))
        values = [item for variant_data in variant_data_list for item in variant_data]

        sql = f"""
            SELECT id FROM variant WHERE (element_id, ref, alt, start, end ) IN ({placeholders});
        """
        self.cursor.execute(sql, values)
        rows = self.cursor.fetchall()

        return None if rows is None else [row["id"] for row in rows]

    def get_sequence(self, element_id: int) -> Optional[str]:
        """
        Returns the sequence of a given element.

        Args:
            element_id (int): The ID of the element.

        Returns:
            Optional[str]: The sequence of the element if it exists, else None.
        """
        sql = "SELECT sequence, type FROM element WHERE id = ?;"
        self.cursor.execute(sql, [element_id])
        row = self.cursor.fetchone()
        return None if row is None else row["sequence"]

    def get_translation_dict(self, translation_id: int) -> Dict[str, str]:
        """
        Returns a dictionary of codon to amino acid mappings for a given translation ID.

        Args:
            translation_id (int): The ID of the translation table.

        Returns:
            Dict[str, str]: A dictionary where each key-value pair represents a codon and its corresponding amino acid.
        """
        sql = "SELECT codon, aa FROM translation WHERE id = ?;"
        self.cursor.execute(sql, [translation_id])
        rows = self.cursor.fetchall()
        return {x["codon"]: x["aa"] for x in rows}

    def get_molecule_ids(
        self, reference_accession: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Returns a dictionary with accessions as keys and respective rowids as values for
        all molecules related to a given (or the default) reference.

        Args:
            reference_accession (str, optional): The reference accession.
            Defaults to None, which means the default reference.

        Returns:
            Dict[str, int]: Dictionary with molecule accessions as keys and their ids as values.
            example: {`molecule.accession`:`molecule.id`} -> {'NC_063383.1': 1}
        """
        if reference_accession:
            if not isinstance(reference_accession, list):
                reference_accession = reference_accession.split(", ")

            condition = (
                "`reference.accession` IN ("
                + ", ".join(["?"] * len(reference_accession))
                + ")"
            )
            val = reference_accession
        else:
            # all outputs
            # condition = "`reference.standard` = ?"
            # val = [1]
            val = [1]
            condition = "1 = ?"

        sql = (
            "SELECT `molecule.accession`, `molecule.id` FROM referenceView WHERE "
            + condition
        )
        self.cursor.execute(sql, val)
        output = {
            x["molecule.accession"]: x["molecule.id"]
            for x in self.cursor.fetchall()
            if x is not None
        }

        return output

    def get_annotation(
        self,
        reference_accession: Optional[str] = None,
        molecule_accession: Optional[str] = None,
        element_accession: Optional[str] = None,
        element_type: Optional[str] = None,
        fields: List[str] = ["*"],
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the annotation based on the given accessions and a type.

        Args:
            reference_accession (str, optional): Accession of the reference. Defaults to None.
            molecule_accession (str, optional): Accession of the molecule. Defaults to None.
            element_accession (str, optional): Accession of the element. Defaults to None.
            element_type (str, optional): Type of the element. Defaults to None.
            fields (List[str], optional): Fields to be selected in the query. Defaults to ["*"].

        Returns:
            List[Dict[str, Any]]: A list of results, each result is a dictionary containing field names as keys and the corresponding data as values.
        """
        # Prepare the conditions and values for the query
        conditions = []
        vals = []

        # Assemble conditions defining accessions or standard elements
        if reference_accession:
            conditions.append("`reference.accession` = ?")
            vals.append(reference_accession)
        else:
            conditions.append("`reference.standard` = ?")
            vals.append(1)
        if molecule_accession:
            conditions.append("`molecule.accession` = ?")
            vals.append(molecule_accession)
        else:
            conditions.append("`molecule.standard` = ?")
            vals.append(1)
        if element_accession:
            conditions.append("`element.accession` = ?")
            vals.append(element_accession)
        elif not element_type:
            conditions.append("`element.type` = ?")
            vals.append("source")
        if element_type:
            conditions.append("`element.type` = ?")
            vals.append(element_type)

        # Construct SQL query to fetch the annotation
        sql = (
            "SELECT "
            + ", ".join(fields)
            + " FROM referenceView WHERE "
            + " AND ".join(conditions)
            + ' ORDER BY "reference.id" ASC, "molecule.id" ASC, "element.id" ASC, "element.segment" ASC;'
        )

        # Execute the query and return the results
        self.cursor.execute(sql, vals)
        rows = self.cursor.fetchall()
        print(rows)
        return rows

    def get_sample_id(self, sample_name: str) -> Optional[int]:
        """
        Returns the rowid of a sample based on its name if it exists, else None is returned.

        Args:
            sample_name (str): Name of the sample.

        Returns:
            Optional[int]: The id of the sample if exists, else None.

        Example usage:
            >>> dbm = getfixture('init_readonly_dbm')
            >>> id = dbm.get_sample_id("seq01")
        """
        sql = "SELECT id FROM sample WHERE name = ? LIMIT 1;"
        self.cursor.execute(sql, [sample_name])
        row = self.cursor.fetchone()
        return None if row is None else row["id"]

    def iter_dna_variants(self, sample_name: str, *element_ids: int) -> Iterator:
        """
        Iterator over DNA variants for a given sample and a list of element IDs.

        Args:
            sample_name (str): Name of the sample to be analyzed.
            *element_ids (int): Variable length argument list of element IDs.

        Returns:
            Iterator[sqlite3.Row]: An iterator that yields rows from the executed SQL query.

        Yields:
            sqlite3.Row: The next row from the executed SQL query.
        """

        if len(element_ids) == 1:
            condition = " = ?"
        elif len(element_ids) > 1:
            condition = " IN (" + ", ".join(["?"] * len(element_ids)) + ")"
        else:
            condition = ""
        # print("Condition:" + condition)
        sql = (
            """ SELECT  variant.element_id as `element.id`,
                    variant.start as `variant.start`,
                    variant.end as  `variant.end`,
                    variant.ref as  `variant.ref`,
                    variant.alt as `variant.alt`
                    FROM
                        ( SELECT sample.seqhash
                        FROM sample
                        WHERE sample.name = ?
                        ) AS sample_T
                    INNER JOIN alignment
                        ON sample_T.seqhash = alignment.seqhash
                    INNER JOIN alignment2variant
                        ON alignment.id = alignment2variant.alignment_id
                    INNER JOIN	variant
                        ON alignment2variant.variant_id = variant.id
                        WHERE  variant.element_id """
            + condition
        )
        self.cursor.execute(sql, [sample_name] + list(element_ids))
        for row in self.cursor.fetchall():
            if row["variant.start"] is not None:
                yield row

    def insert_sample(self, sample_name, seqhash):
        """
        Inserts or updates a sample/genome in the database and returns the sample id.

        Args:
            sample_name (str): The name of the sample to be inserted or updated in the database.
            seqhash (str): The hash of the sequence to be associated with the sample.

        Returns:
            int: The sample id of the inserted or updated sample.


        >>> rowid = dbm.insert_sample("my_new_sample", "1a1f34ef4318911c2f98a7a1d6b7e9217c4ae1d1")

        """
        self.insert_sequence(seqhash)
        # NOTE:Right now we use INSERT IGNORE INTO,
        # in the future, we might want to use ON DUP
        # example
        # INSERT INTO ..... ON DUPLICATE KEY UPDATE name=VALUES(name), seqhash=VALUES(seqhash),
        # "REPLACE INTO sample (name, seqhash, datahash) VALUES(?, ?, ?);"

        sql = "INSERT IGNORE INTO sample (name, seqhash, datahash) VALUES(?, ?, ?);"
        self.cursor.execute(sql, [sample_name, seqhash, ""])
        sql = "SELECT id FROM sample WHERE name = ?;"
        self.cursor.execute(sql, [sample_name])
        sid = self.cursor.fetchone()
        if sid:
            sid = sid["id"]

        for pname in self.properties:
            if not self.properties[pname]["standard"] is None:
                self.insert_property(sid, pname, self.properties[pname]["standard"])

        # check if it was already exist or not.
        row = self.get_property_IMPORTDATE(sid=sid)
        if row is None:
            # add INSERTED DATE
            value = datetime.date.today()
            self.insert_property(sid, "IMPORTED", value)
        else:
            pass
            # print("PASS")

        return sid

    def insert_sequence(self, seqhash):
        """
        Inserts a sequence represented by its hash to the database. If the hash is already known, it is ignored.

         Args:
             seqhash (str): The hash of the sequence to be inserted into the database.


         >>> dbm = getfixture('init_writeable_dbm')
         >>> dbm.insert_sequence("1a1f34ef4318911c2f98a7a1d6b7e9217c4ae1d1")

        """
        sql = "INSERT IGNORE INTO sequence (seqhash) VALUES(?);"
        self.cursor.execute(sql, [seqhash])

    def get_element_ids(
        self,
        reference_accession: Optional[str] = None,
        element_type: Optional[str] = None,
    ) -> List[str]:
        """
        Returns ids of elements given a reference accession and a type.

        This molecule_ids will return all ids if reference_accession is None

        Args:
            reference_accession (str, optional): The accession of the reference. Defaults to None (standard reference ist used).
            element_type (str, optional): The type of the element. Defaults to None.

        Returns:
            List[str]: A list of element ids.
        """
        # Get the molecule ids base on given reference accession
        molecule_ids = list(
            self.get_molecule_ids(reference_accession=reference_accession).values()
        )

        if len(molecule_ids) == 0:
            LOGGER.error("No reference match was found.")
            LOGGER.warning(
                "This situation can arise when the reference has already been removed from the database."
            )
            LOGGER.info(
                "Kindly add the reference and then continue with re-export/import processes again."
            )
            sys.exit(1)
        # Construct SQL query
        query = (
            "SELECT id FROM element WHERE molecule_id IN ("
            + ", ".join(["?"] * len(molecule_ids))
            + ")"
        )

        # Add type to the query if provided
        if element_type:
            query += " AND type = ?"
            molecule_ids.append(element_type)

        # Execute query
        self.cursor.execute(query, molecule_ids)
        rows = self.cursor.fetchall()

        # Return an empty list if no result found, otherwise return the list of ids
        return [] if not rows else [x["id"] for x in rows]

    def get_property_IMPORTDATE(self, sid=None):
        row = None
        if sid:
            sql = "SELECT property_id FROM sample2property WHERE sample_id = ? AND property_id= 1;"
            self.cursor.execute(sql, [sid])
            row = self.cursor.fetchone()
        return row

    def get_alignment_by_seqhash(self, seqhash):
        """
        Returns the rowid of a sample based on the respective seqhash  If no
        alignment of the given sequence hash, it will return empty list.

        Check if there is a sample that doesn't align to any reference.
        """
        sql = "SELECT id FROM alignment WHERE seqhash = ? ;"
        self.cursor.execute(sql, [seqhash])
        row = self.cursor.fetchall()
        if not row:
            return []
        return [x["id"] for x in row]

    def insert_alignment(self, seqhash, element_id):
        """
        Inserts a sequence-alignment relation into the database if not existing and returns the row id.

        Args:
            seqhash (str): The hash of the sequence to be associated with the alignment.
            element_id (int): The element id to be associated with the alignment.

        Returns:
            int: The row id of the inserted alignment.

        >>> rowid = dbm.insert_alignment("1a1f34ef4318911c2f98a7a1d6b7e9217c4ae1d1", 1)

        """
        # NOTE: remove id from SQL stm. (Auto-increment ID)
        # sql = "INSERT IGNORE INTO alignment (id, seqhash, element_id) VALUES(?, ?, ?);"
        # self.cursor.execute(sql, [None, seqhash, element_id])
        sql = "INSERT IGNORE INTO alignment ( seqhash, element_id) VALUES( ?, ?);"
        self.cursor.execute(sql, [seqhash, element_id])

        # Retrieve the alignment ID
        sql = "SELECT id FROM alignment WHERE element_id = ? AND seqhash = ?;"
        self.cursor.execute(sql, [element_id, seqhash])

        rowid = self.cursor.fetchone()
        if rowid:
            rowid = rowid["id"]
        else:
            LOGGER.error("Cannot get rowid:", rowid)
            sys.exit(1)
        return rowid

    def insert_variant_many(self, row_list, alignment_id):
        """
        Improved Version of insert variant
        instead of one by one, we use executemany to improve insertion time.

        row_list = [(
        element_id, 0
        ref, 1
        alt, 2
        start, 3
        end, 4
        label, 5
        frameshift, 6
        )]

        updated_var_row_list = [(id 0, element_id 1, pre_ref 2, start 3, end 4, ref 5, alt 6,
        label 7, parent_id 8, frameshift 9)]
        """
        updated_var_row_list = []
        insert_var_row_list = []
        parent_id = ""
        ref_dict = self.sequence_references

        for row in row_list:

            try:
                # Convert the old tuple to a list to modify it
                updated_list = list(row)

                selected_ref_seq = ref_dict[int(row[0])]
                if int(row[3]) <= 0:
                    pre_ref = ""
                else:
                    pre_ref = selected_ref_seq[int(row[3]) - 1]

            except KeyError:
                # KeyError for a case of Amino Acid, we don't stroe these information at this moment.
                # logging.warn(e)
                pre_ref = ""

            # Insert None (*ID) at position 0
            updated_list.insert(0, None)
            # Insert pre_ref at position 2
            updated_list.insert(2, pre_ref)
            updated_list.insert(8, parent_id)

            # Deduplicate variants...
            # Check varaint if exist
            vid = self.get_variant_id(
                updated_list[1],
                int(updated_list[5]),
                int(updated_list[6]),
                updated_list[3],
                updated_list[4],
            )

            # STILL keep all variants for next step alignment2variant
            updated_var_row_list.append(tuple(updated_list))

            # if it exists, we will not insert......
            if vid is None:
                # Convert the updated list back to a tuple and append to the new list
                insert_var_row_list.append(tuple(updated_list))

        if len(insert_var_row_list) > 0:
            sql = "INSERT IGNORE INTO variant (id, element_id, pre_ref, ref, alt, start, end, label, parent_id, frameshift) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
            self.cursor.executemany(sql, insert_var_row_list)

        updated_alignment2variant_list = []
        variant_data_list = []
        # st = time.time()  # NOTE!!: Slow Performance
        for row in updated_var_row_list:
            """
            element_id = row[1]
            start = row[3]
            end = row[4]
            ref = row[5]
            alt = row[6]
            """
            variant_data_list.append((row[1], row[3], row[4], row[5], row[6]))
        _data_list = self.get_variant_ids(variant_data_list)

        for row_id in _data_list:
            updated_alignment2variant_list.append((alignment_id, row_id))

        sql = "INSERT IGNORE INTO alignment2variant (alignment_id, variant_id) VALUES(?, ?);"
        self.cursor.executemany(sql, updated_alignment2variant_list)

    # IMPORT SAMPLE DATA
    def insert_property(
        self, sample_id: int, property_name: str, property_value: Union[str, int, float]
    ) -> None:
        """
        NOTE: change execute to executemany to increase performance.

        Inserts/Updates a property value of a given sample in the database.

        Args:
            sample_id (int): The ID of the sample for which the property is being updated.
            property_name (str): The name of the property being updated.
            property_value (Union[str, int, float]): The value of the property being updated.

        Raises:
            Error: If an error occurs while interacting with the database.

        Example usage:
            >>> dbm = getfixture('init_writeable_dbm')
            >>> dbm.insert_property(1, "LINEAGE", "BA.5")
        """
        if property_name in self.__illegal_properties:
            LOGGER.error("This proprty name is reserved and cannot be used.")
            sys.exit(1)

        try:
            sql = (
                f"INSERT INTO {self.properties[property_name]['target']}2property (sample_id, property_id, value_"
                + self.properties[property_name]["datatype"]
                + ") VALUES(?, ?, ?)"
                + " ON DUPLICATE KEY UPDATE value_"
                + self.properties[property_name]["datatype"]
                + "=?"
            )
            # tmp solution for insert empty date
            # Incorrect date value: ''
            if self.properties[property_name]["datatype"] == "date":
                if property_value == "":
                    property_value = None

            self.cursor.execute(
                sql,
                [
                    sample_id,
                    self.properties[property_name]["id"],
                    property_value,
                    property_value,
                ],
            )

        except Exception as e:
            LOGGER.error(e)
            LOGGER.error(
                f"[insert property] Sample ID:'{str(sample_id)}' cannot be processed"
            )
            sys.exit("If you need an assistance, please contact us.")

    # DELETE DATA
    def delete_seqhash(self, seqhash):
        sql = "DELETE FROM sequence WHERE seqhash = ?;"
        self.cursor.execute(sql, [seqhash])

    def delete_alignment(self, seqhash=None, element_id=None):
        condition = ""

        if seqhash:
            condition = f" seqhash = '{seqhash}'"
        if element_id:
            if condition:
                condition = condition + f" AND element_id = '{element_id}'"
            else:
                condition = f" element_id = '{element_id}'"
        if not condition:
            LOGGER.info("Nothing to delete an alignment")
            return

        sql = f"DELETE FROM alignment WHERE {condition};"
        self.cursor.execute(sql)

    def delete_samples(self, *sample_names: str) -> None:
        """
        Deletes one or more given samples based on their names if they exist in the database.

        Args:
            sample_names (str): The names of the samples to be deleted.

        Example usage:
            >>> dbm.delete_samples("NC_045512")
        """
        sample_names = list(set(sample_names))
        sql = (
            "DELETE FROM sample WHERE name IN ("
            + ", ".join(["?"] * len(sample_names))
            + ");"
        )
        self.cursor.execute(sql, sample_names)
        # self.clean()

    def clean(self) -> None:
        """
        Clean the database by removing data from tables where certain conditions are not met.
        """
        # SQL queries for cleanup
        cleanup_queries = [
            "DELETE FROM sequence WHERE NOT EXISTS(SELECT NULL FROM sample WHERE sample.seqhash = seqhash)",
            "DELETE FROM sample2property WHERE NOT EXISTS(SELECT NULL FROM sample WHERE sample.id = sample_id) OR NOT EXISTS(SELECT NULL FROM property WHERE property.id = property_id)",
            "DELETE FROM variant2property WHERE NOT EXISTS(SELECT NULL FROM variant WHERE variant.id = variant_id) OR NOT EXISTS(SELECT NULL FROM property WHERE property.id = property_id)",
            "DELETE FROM translation WHERE NOT EXISTS(SELECT NULL FROM reference WHERE reference.translation_id = id)",
            "DELETE FROM molecule WHERE NOT EXISTS(SELECT NULL FROM reference WHERE reference.id = reference_id)",
            "DELETE FROM element WHERE NOT EXISTS(SELECT NULL FROM molecule WHERE molecule.id = molecule_id)",
            "DELETE FROM elempart WHERE NOT EXISTS(SELECT NULL FROM element WHERE element.id = element_id)",
            "DELETE FROM variant WHERE NOT EXISTS(SELECT NULL FROM alignment2variant WHERE alignment2variant.variant_id = variant_id)",
            "DELETE FROM alignment WHERE NOT EXISTS(SELECT NULL FROM sequence WHERE sequence.seqhash = seqhash) OR NOT EXISTS(SELECT NULL FROM element WHERE element.id = element_id)",
            "DELETE FROM alignment2variant WHERE NOT EXISTS(SELECT NULL FROM alignment WHERE alignment.id = alignment_id)",
        ]

        # Execute each cleanup query
        for query in cleanup_queries:
            self.cursor.execute(query)

    def get_seq_hash(self, sample_name):
        sql = "SELECT seqhash FROM sample WHERE name = ? ;"
        self.cursor.execute(sql, [sample_name])
        row = self.cursor.fetchone()
        return row

    def match(
        self,
        profiles: Optional[Tuple[str, ...]] = None,
        samples: Optional[List[str]] = None,
        reference_accession: Optional[str] = None,
        properties: Optional[Dict[str, List[str]]] = None,
        frameshifts_only: Optional[bool] = False,
        filter_n: Optional[bool] = True,
        filter_x: Optional[bool] = True,
        ignore_terminal_gaps: Optional[bool] = True,
        output_columns: Optional[List[str]] = None,
        format: Optional[str] = "csv",
    ) -> Union[List[Dict[str, str]], str]:
        """
        This function matches samples based on their metadata and genomic profiles.

        Args:
            profiles (Optional[Tuple[str, ...]], optional): List of profiles to match. Defaults to None.
            samples (Optional[List[str]], optional): List of samples to consider. Defaults to None.
            reference_accession (str): Reference accession to construct the conditions for the SQL query.
            properties (Optional[Dict[str, List[str]]], optional): Dictionary of properties to filter samples. Defaults to None.
            frameshifts_only (Optional[bool], optional): Whether to consider only frameshifts. Defaults to False.
            filter_n (Optional[bool], optional): Whether to filter 'N'. Defaults to True.
            filter_x (Optional[bool], optional): Whether to filter 'X'. Defaults to True.
            ignore_terminal_gaps (Optional[bool], optional): Whether to ignore terminal gaps. Defaults to True.
            output_columns (Optional[List[str]], optional): List of output columns. Defaults to None.
            format (Optional[str], optional): Output format. It can be "csv", "tsv", "count", "vcf". Defaults to "csv".

        Returns:
            Union[List[Dict[str, str]], str]: Returns the matched samples in the requested format.

        Raises:
            SystemExit: If the provided output format is not supported.
        """

        (
            sample_selection_query,
            sample_selection_values,
        ) = self.create_sample_selection_sql(
            samples, properties, profiles, frameshifts_only, reference_accession
        )

        if format == "csv" or format == "tsv":
            return self.handle_csv_tsv_format(
                sample_selection_query,
                sample_selection_values,
                reference_accession,
                filter_n,
                filter_x,
                ignore_terminal_gaps,
                output_columns,
            )
        elif format == "count":
            return self.handle_count_format(
                sample_selection_query, sample_selection_values
            )
        elif format == "vcf":
            return self.handle_vcf_format(
                sample_selection_query,
                sample_selection_values,
                reference_accession,
                filter_n,
                ignore_terminal_gaps,
            )
        else:
            LOGGER.error(f"'{format}' is not a valid output format.")
            sys.exit(1)

    def handle_vcf_format(
        self,
        sample_selection_sql: str,
        sample_selection_values: List[str],
        reference_accession: str,
        filter_n: str,
        ignore_terminal_gaps: str,
    ) -> List[Dict[str, str]]:
        """
        Fetches data in VCF format based on the given parameters.

        Args:
            sample_selection_sql (str): SQL query to select the samples.
            sample_selection_values (List[str]): Values for property-based filtering.
            reference_accession (str): Reference accession to construct the conditions for the SQL query.
            filter_n (str): Condition for handling 'N' variants.
            filter_terminal_gaps (str): Condition for handling terminal gap variants.
        Returns:
            List[Dict[str, str]]: List of dictionaries where each dictionary represents a row in the resulting VCF file.
        """
        genome_condition, _ = self.create_genomic_element_conditions(
            reference_accession, element_alias="e", molecule_alias="m"
        )
        nuc_filter, _ = self.create_special_variant_filter_conditions(
            filter_n, False, ignore_terminal_gaps
        )

        sql = f"""SELECT
                    _rows.element_id AS "element.id",
                    _rows.type AS "element.type",
                    _rows.accession AS "molecule.accession",
                    _rows.id AS "variant.id",
                    _rows.start AS "variant.start",
                    _rows.end AS "variant.end",
                    _rows.pre_ref AS "variant.pre_ref",
                    _rows.ref AS "variant.ref",
                    _rows.alt AS "variant.alt",
                    _rows.label AS "variant.label",
                    GROUP_CONCAT(_rows.name) as samples
                FROM
                (
                    SELECT
                        fs.sample_id,
                        fs.name,
                        fs.seqhash,
                        v.id,
                        v.start,
                        v.label,
                        v.end,
                        v.pre_ref,
                        v.ref,
                        v.alt,
                        v.element_id,
                        e.type,
                        m.accession
                    FROM (
                        {sample_selection_sql}
                    ) AS fs
                    LEFT JOIN alignment a ON fs.seqhash = a.seqhash
                    LEFT JOIN alignment2variant a2v ON a.id = a2v.alignment_id
                    LEFT JOIN variant v ON a2v.variant_id = v.id
                    LEFT JOIN element e ON v.element_id = e.id
                    LEFT JOIN molecule m ON e.molecule_id = m.id
                    WHERE {genome_condition}{nuc_filter}
                ) as _rows
                GROUP BY
                    _rows.accession, _rows.start, _rows.ref, _rows.alt
                ORDER BY
                    _rows.accession, _rows.start;
        """
        # print(sql, sample_selection_values)
        self.cursor.execute(sql, sample_selection_values)

        return self.cursor.fetchall()

    def create_sample_selection_sql(  # noqa: C901
        self,
        samples: Optional[List[str]] = None,
        properties: Optional[Dict[str, List[str]]] = None,
        profiles: Optional[Dict[str, List[str]]] = None,
        frameshifts_only: bool = None,
        reference_accession: str = None,
    ) -> Tuple[str, List[str]]:
        """
        Create a SQL query and corrspond value list to rertieve sample IDs based on the given sample names, properties, and genomic profiles.

        Args:
            samples (Optional[List[str]]): A list of samples to consider for query creation. Default is None.
            properties (Optional[Dict[str, List[str]]]): A dictionary of properties for query creation. Default is None.
            profiles (Optional[Dict[str, List[str]]]): A dictionary of profiles for query creation. Default is None.
            frameshifts_only (bool): If true, consider samples with frameshift mutations only.

        Returns:
            Tuple[str, List[str]]: A SQL query to retrieve matching sample IDs and a list of property and profile values.
        """

        conditions = []
        vals = []

        conditions_profile = []
        conditions_properties = []

        # SECTION:
        # NOTE: Find the refID, if refID is not given,
        # this will return all refIDs that match the given profiles
        selected_ref_ids = None

        # WARN: this take only one accession ID into account at a time. *not support multiple refs.
        if reference_accession:
            selected_dict = next(
                item
                for item in self.references
                if item["accession"] == reference_accession
            )
            selected_ref_ids = str(selected_dict["id"])
        else:
            # guest from variant
            if len(profiles) > 0:
                ref_id_list = self.get_ref_variant_ID(profiles)
                selected_ref_ids = ", ".join([str(x) for x in ref_id_list])
            else:
                # WARN: What if no profiles are given??
                # The current solution: it will use default ref.
                pass
        LOGGER.debug(f"Using reference ID (molecule accesion): {selected_ref_ids}")

        # SECTION: set framsehift-related table data
        if frameshifts_only:
            table = """(
                        SELECT DISTINCT sample.id AS id, sample.name AS name, sample.seqhash AS seqhash
                        FROM sample
                        JOIN alignment ON sample.seqhash = alignment.seqhash
                        JOIN alignment2variant ON alignment.id = alignment2variant.alignment_id
                        JOIN variant ON alignment2variant.variant_id = variant.id
                        WHERE variant.frameshift = 1
                    )"""
        else:
            table = "sample"

        # SECTION: add properties- and profile-related conditions
        cases = []

        property_cases, property_conditions, property_vals = (
            self.create_sample_property_case(properties) if properties else ([], [], [])
        )

        profile_cases, profile_conditions, profile_vals = (
            self.create_profile_cases(*profiles) if profiles else ([], [], [])
        )

        sql = "SELECT DISTINCT sub.sample_id, sub.name, sub.seqhash, sub.accession FROM (SELECT DISTINCT s.id AS 'sample_id', s.name , s.seqhash, molecule.accession "
        joins = ""

        # SECTION:
        # add joins and cases for sample propetries

        # inside table * sub
        if property_cases:
            joins += """JOIN sample2property ON s.id = sample2property.sample_id\n
                     """
            cases.extend(property_cases)
            if property_conditions:
                if len(profile_conditions) == 1:
                    conditions_properties.extend(property_conditions)
                else:
                    conditions_properties.append(
                        "(" + " AND ".join(property_conditions) + ")"
                    )
            vals.extend(property_vals)
        # SECTION:
        # add joins and cases for genome profiles
        """
        if profile_cases:
            joins += JOIN alignment ON s.seqhash = alignment.seqhash
                    JOIN alignment2variant ON alignment.id = alignment2variant.alignment_id
                    JOIN variant ON alignment2variant.variant_id = variant.id
                    JOIN element ON variant.element_id = element.id
                    JOIN molecule ON element.molecule_id = molecule.id\n

            cases.extend(profile_cases)
            if len(profile_conditions) == 1:
                conditions_profile.extend(profile_conditions)
            else:
                conditions_profile.append("(" + " OR ".join(profile_conditions) + ")")
            vals.extend(profile_vals)
        """
        # make this join permanent, as we require the molecule ID., the above code part was used in previous version.
        joins += """JOIN alignment ON s.seqhash = alignment.seqhash
                    JOIN alignment2variant ON alignment.id = alignment2variant.alignment_id
                    JOIN variant ON alignment2variant.variant_id = variant.id
                    JOIN element ON variant.element_id = element.id
                    JOIN molecule ON element.molecule_id = molecule.id\n"""

        # inside table * sub
        if profile_cases:
            cases.extend(profile_cases)

            if len(profile_conditions) == 1:
                conditions_profile.extend(profile_conditions)
            else:
                conditions_profile.append("(" + " OR ".join(profile_conditions) + ")")

            vals.extend(profile_vals)

        if cases:
            sql += ", " + ", ".join(cases)
            sql += f" FROM {table} s"
        else:
            sql += f" FROM {table} s"

        sql += " " + joins + " "

        # SECTION: sample
        # add sample-related condition
        if len(samples) == 1:
            conditions.append("s.name = ?")
            vals.extend(samples)
        elif len(samples) > 1:
            sample_wildcards = ", ".join(["?"] * len(samples))
            conditions.append(f"s.name IN ({sample_wildcards})")
            vals.extend(samples)

        # SECTION:
        # add reference ID condition
        # NOTE: this part could be inserted at profile case. to narrow down the varaints before join ops.
        if selected_ref_ids:
            conditions.append(f" molecule.id IN ({selected_ref_ids}) ")

        # SECTION:
        if conditions:
            conditions = " AND ".join(conditions)
            sql += f" WHERE {conditions} GROUP BY s.id "
            # sql += f" WHERE {conditions}" <--- cannot
        sql += ") AS sub"

        # SECTION: ------ outside sub... ------
        if conditions_properties:
            conditions_properties = " AND ".join(conditions_properties)
            sql += f" WHERE {conditions_properties}"

        if conditions_profile:  # <-- add another condition profile variable.
            # to put it at WHERE clause outside "sub", because it cannot be inside sub.
            # e.g., mutation_1 = 1
            conditions_profile = " AND ".join(conditions_profile)

            if conditions_properties:  # means already have WHERE clause
                sql += f" AND {conditions_profile}"
            else:
                sql += f" WHERE {conditions_profile}"

        # sql += " GROUP BY sub.sample_id"

        sql = self.format_sql(sql)
        LOGGER.debug(f"sample_selection: {sql}")
        LOGGER.debug("------------------")
        return sql, vals

    def create_sample_property_case(
        self,
        properties: Optional[
            Dict[str, Tuple[str, List[Union[str, int, float]]]]
        ] = None,
    ) -> Tuple[List[str], List[str], List[Union[str, int, float]]]:
        """
        Create SQL WHERE clause for sample metadata-based filtering.

        Args:
            properties: A dictionary mapping property names to a list of their values.

        Returns:
            A tuple where:
                - first element is a list of CASE statements,
                - second element is a list of WHERE conditions,
                - third element is a list of values associated with the queries.
        """
        property_cases = []
        property_conditions = []
        property_vals = []

        if not properties:
            return property_conditions, property_cases, property_vals

        pid = 0
        for pname, vals in properties.items():
            if not vals:
                continue
            pid += 1
            case, val = self.build_sample_property_condition(pname.lstrip("."), *vals)
            property_cases.append(
                f"SUM(CASE WHEN {' AND '.join(case)} THEN 1 ELSE 0 END) AS property_{pid}"
            )
            property_conditions.append(f"property_{pid} >= 1")
            property_vals.extend(val)

        return property_cases, property_conditions, property_vals

    def create_profile_cases(
        self, *profiles: Tuple[str, ...]
    ) -> Tuple[List[str], List[str], List[Union[str, int, float]]]:
        """
        Create SQL CASE and WHERE clauses for genomic profile-based filtering.

        Args:
            profiles: A list of tuples, where each tuple contains variant notations representing a genomic profile.

        Returns:
            A tuple where:
                - first element is a list of CASE statements,
                - second element is a list of WHERE conditions,
                - third element is a list of values associated with the query.
        """
        regexes = {
            "snv": re.compile(r"^(|[^:]+:)?([^:]+:)?([A-Z]+)([0-9]+)(=?[A-Zxn]+)$"),
            "del": re.compile(r"^(|[^:]+:)?([^:]+:)?del:(=?[0-9]+)(|-=?[0-9]+)?$"),
        }

        processing_funcs = {
            "snv": self.build_snp_and_insert_condition,
            "del": self.build_deletion_condition,
        }

        ids = {}
        cases = []
        wheres = []
        vals = []

        for profile in profiles:
            where_conditions = []

            for mutation in profile:
                count = 1 if not mutation.startswith("^") else 0
                mutation = mutation.lstrip("^")

                # create case if novel mutation
                if mutation not in ids:
                    ids[mutation] = len(ids) + 1
                    for mutation_type, regex in regexes.items():
                        match = regex.match(mutation)
                        if match:
                            case, val = processing_funcs[mutation_type](match)
                            cases.append(
                                f"SUM(CASE WHEN {' AND '.join(case)} THEN 1 ELSE 0 END) AS mutation_{ids[mutation]}"
                            )
                            vals.extend(val)
                            break
                    if not match:
                        LOGGER.error(f"Invalid mutation notation '{mutation}'.")
                        sys.exit(1)

                if count == 0:
                    where_conditions.append(f"mutation_{ids[mutation]} = {count}")
                else:
                    where_conditions.append(f"mutation_{ids[mutation]} >= {count}")

            if len(where_conditions) == 1:
                wheres.extend(where_conditions)
            elif len(where_conditions) > 1:
                wheres.append("(" + " AND ".join(where_conditions) + ")")

        print(wheres)
        return cases, wheres, vals

    def create_genomic_element_conditions(
        self,
        reference_accession: str,
        element_alias: Optional[str] = "element",
        molecule_alias: Optional[str] = "molecule",
    ) -> Tuple[str, str]:
        """
        Generate the genomic element conditions for the SQL query.

        Args:
            reference_accession (str): The reference accession to create genomic element conditions.
            element_alias: ALisas used for element table
            molecule_alias: ALisas used for molecule table

        Returns:
            Tuple[str, str]: A tuple containing the genomic element condition and the molecule prefix.
        """
        element_ids = self.get_element_ids(reference_accession, "source")
        if len(element_ids) == 1:
            genome_element_condition = f"{element_alias}.id = {element_ids[0]}"
            molecule_prefix = ""
        else:
            formatted_ids = ", ".join(map(str, element_ids))
            genome_element_condition = f"{element_alias}.id IN ({formatted_ids})"
            molecule_prefix = f'{molecule_alias}.symbol || "@" || '

        return genome_element_condition, molecule_prefix

    def create_special_variant_filter_conditions(
        self, filter_n: bool, filter_x: bool, ignore_terminal_gaps: bool
    ) -> Tuple[str, str]:
        """
        Create query conditions for special variants such as ambiguities and terminal gaps.

        Args:
            filter_n (bool): Flag for handling 'N' variants.
            filter_x (bool): Flag for handling 'X' variants.
            ignore_terminal_gaps (bool): Flag for handling terminal gap variants.

        Returns:
            Tuple[str, str]: A tuple containing the nucleotide filter and amino acid filter conditions.
        """

        # process mutation display filters
        aa_filter = " AND alt != 'X'" if filter_x else ""
        nuc_filter = []
        if filter_n:
            nuc_filter.append("alt != 'N'")
        if ignore_terminal_gaps:
            nuc_filter.append("alt != '.'")
        nuc_filter = " AND " + " AND ".join(nuc_filter) if nuc_filter else ""
        return nuc_filter, aa_filter
