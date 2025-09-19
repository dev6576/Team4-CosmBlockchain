#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import argparse
import pathlib
import psycopg2
import os
import requests

FEATURE_TYPE_TEXT = "Digital Currency Address - "
NAMESPACE = {'sdn': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'}

POSSIBLE_ASSETS = ["XBT", "ETH", "XMR", "LTC", "ZEC", "DASH", "BTG", "ETC",
                   "BSV", "BCH", "XVG", "USDT", "XRP", "ARB", "BSC", "USDC",
                   "TRX"]

OUTPUT_FORMATS = ["TXT", "DB"]

DEFAULT_SDN_PATH = os.path.join(os.path.dirname(__file__), "sdn_advanced.xml")

DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5433
}

SDN_URL = "https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml"
LOCAL_PATH = DEFAULT_SDN_PATH

def download_sdn_xml():

    print(f"[INFO] Downloading latest SDN XML from OFAC...")
    response = requests.get(SDN_URL)
    response.raise_for_status()  # will raise an error if the download fails

    with open(LOCAL_PATH, 'wb') as f:
        f.write(response.content)

    print(f"[INFO] SDN XML downloaded successfully to {LOCAL_PATH}")
    return LOCAL_PATH

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Tool to extract sanctioned digital currency addresses from the OFAC SDN XML')
    parser.add_argument('assets', choices=POSSIBLE_ASSETS, nargs='*',
                        default=POSSIBLE_ASSETS[0], help='the asset for which the sanctioned addresses should be extracted')
    parser.add_argument('-sdn', '--special-designated-nationals-list', dest='sdn', type=argparse.FileType('rb'),
                        help='path to sdn_advanced.xml', default=DEFAULT_SDN_PATH)
    parser.add_argument('-f', '--output-format',  dest='format', nargs='*', choices=OUTPUT_FORMATS,
                        default=OUTPUT_FORMATS[0], help='output format (TXT or DB)')
    parser.add_argument('-path', '--output-path', dest='outpath',  type=pathlib.Path, default=pathlib.Path("./"),
                        help='path for TXT output')
    return parser.parse_args()


def feature_type_text(asset):
    return FEATURE_TYPE_TEXT + asset


def get_address_id(root, asset):
    feature_type = root.find(
        "sdn:ReferenceValueSets/sdn:FeatureTypeValues/*[.='{}']".format(feature_type_text(asset)), NAMESPACE)
    if feature_type is None:
        raise LookupError(f"No FeatureType with the name {feature_type_text(asset)} found")
    return feature_type.attrib["ID"]


def get_sanctioned_addresses(root, address_id):
    addresses = []
    for feature in root.findall("sdn:DistinctParties//*[@FeatureTypeID='{}']".format(address_id), NAMESPACE):
        for version_detail in feature.findall(".//sdn:VersionDetail", NAMESPACE):
            addresses.append(version_detail.text)
    return addresses



def write_addresses_db(addresses, asset):
    print(f"[INFO] Connecting to database {DB_CONFIG['dbname']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    inserted_count = 0
    for address in addresses:
        try:
            cur.execute(
            """
            INSERT INTO flagged_wallets (wallet_id, reason, risk_score)
            VALUES (%s, %s, %s)
            ON CONFLICT (wallet_id) DO UPDATE
            SET reason = EXCLUDED.reason,
                risk_score = EXCLUDED.risk_score
            """,
            (address, f"OFAC Sanctioned Wallet", 10)
            )
            inserted_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to insert {address}: {e}")
    conn.commit()
    cur.close()
    conn.close()
    print(f"[INFO] Database insertion completed. {inserted_count} addresses processed.")


def main():
    sdn_file_path = download_sdn_xml()
    args = parse_arguments()
    print(f"[INFO] Loading SDN XML file from: {sdn_file_path}")
    tree = ET.parse(sdn_file_path)
    root = tree.getroot()
    print("[INFO] SDN XML loaded successfully.")

    assets = args.assets if isinstance(args.assets, list) else [args.assets]
    output_formats = args.format if isinstance(args.format, list) else [args.format]

    for asset in assets:
        print(f"\n[INFO] Processing asset: {asset}")
        try:
            address_id = get_address_id(root, asset)
        except LookupError as e:
            print(f"[WARNING] {e}")
            continue
        addresses = get_sanctioned_addresses(root, address_id)
        print(f"[INFO] Found {len(addresses)} sanctioned addresses for {asset}.")

        # deduplicate and sort
        addresses = sorted(list(dict.fromkeys(addresses).keys()))
        print(f"[INFO] {len(addresses)} addresses after deduplication and sorting.")

        write_addresses_db(addresses, asset)

    print("\n[INFO] All assets processed successfully.")


if __name__ == "__main__":
    main()
