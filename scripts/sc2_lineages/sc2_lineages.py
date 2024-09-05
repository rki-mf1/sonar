## run command: python sc2_lineages.py -o sc2_lineages.tsv

import argparse
import pandas as pd
from pango_aliasor.aliasor import Aliasor

def get_sublineages(df, lineage):
    sublineages = df[df['parent'] == lineage]['lineage'].tolist()
    return ','.join(sublineages) if sublineages else 'none'


def main():

    parser = argparse.ArgumentParser(description='Create file with all pangolin lineages mapped to their direct sublineages.')
    parser.add_argument('-o', '--output', type=str, help='Path and name of output tsv file.')
    # parser.add_argument('-r', '--recombinants', type=bool, help='wether to include recombined lineages as sublineages.')

    args = parser.parse_args()
    output_file = args.output
    # include_recombinants = args.recombinants

    path_lineages = "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/lineage_notes.txt"
    all_lineages = [lineage for lineage in pd.read_csv(path_lineages, sep='\t').iloc[:, 0].tolist()  if not lineage.startswith('*')]
    
    aliasor = Aliasor() # If no alias_key.json is passed, downloads the latest version from github # Aliasor('alias_key.json')
    df = pd.DataFrame({'lineage': all_lineages, 
                       'parent': ['none' if aliasor.parent(lineage) == '' else aliasor.parent(lineage) for lineage in all_lineages], # e.g: aliasor.parent("BQ.1") # 'BE.1.1.1'
                       'sublineages': None
    }) 
    # for each lineage get the DIRECT sublineages
    df['sublineages'] = df['lineage'].apply(lambda x: get_sublineages(df, x))

    df[['lineage', 'sublineages']].to_csv(output_file, sep='\t', index=False)

    return 0

if __name__ == "__main__":
    main()
