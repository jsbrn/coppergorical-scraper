import re
import requests
from bs4 import BeautifulSoup


BLOCK_CATEGORIES_URL = "https://minecraft.wiki/w/Category:Blocks"
ITEM_CATEGORIES_URL = "https://minecraft.wiki/w/Category:Items"

BLOCK_LIST_URL = "https://minecraft.wiki/w/Java_Edition_data_values/Blocks"
ITEM_LIST_URL = "https://minecraft.wiki/w/Java_Edition_data_values/Items"
MOB_LIST_URL = "https://minecraft.wiki/w/Mob"

NETHER_URL = "https://minecraft.wiki/w/The_nether"
END_URL = "https://minecraft.wiki/w/The_end"

# Use this to define category renames
category_renames = {
    "the_nether": "nether",
    "the_end": "end",
    "utilities": "utility"
}

name_to_id_map = {}
id_to_categories_map = {}

def sanitize_name(name: str) -> str:
    return name.lower().replace("(item)", "").replace("(block)", "").replace("(", "").replace(")", "").strip()

def to_id(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[^A-Za-z0-9\s]+', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name.lower()

def extract_names(s: str) -> list[str]:
    cats = s.split('/')
    return [to_id(cat) for cat in cats]

def add_categories_to_item(item: str, categories: list[str]):
    if item not in id_to_categories_map:
        id_to_categories_map[item] = []
    for category in categories:
        category = category_renames.get(category, category)
        if category not in id_to_categories_map[item]:
            id_to_categories_map[item].append(category)


def fetch_block_name_map():
    print("MAPPING BLOCK NAMES TO ID")
    response = requests.get(BLOCK_LIST_URL)
    html = response.text
    soup = BeautifulSoup(html, features="lxml")
    table = soup.find("table", class_="sortable")
    rows = table.find_all("tr")
    for row in rows:
        columns = row.find_all("td")
        if len(columns) > 0:
            #print(list(columns))
            block_name = sanitize_name(columns[2].text)
            block_id = columns[1].text.strip()
            item_id = columns[3].text.strip()
            effective_id = block_id if item_id == "Identical" else item_id
            name_to_id_map[block_name] = effective_id
            print("  " + block_name + " >>> " + effective_id)

def fetch_item_name_map():
    print("MAPPING ITEM NAMES TO ID")
    response = requests.get(ITEM_LIST_URL)
    html = response.text
    soup = BeautifulSoup(html, features="lxml")
    table = soup.find("table", class_="sortable")
    rows = table.find_all("tr")
    for row in rows:
        columns = row.find_all("td")
        if len(columns) > 0:
            #print(list(columns))
            item_name = sanitize_name(columns[0].text)
            item_id = columns[1].text.strip()
            name_to_id_map[item_name] = item_id
            print("  " + item_name + " >>> " + item_id)

def fetch_wiki_categories(url: str):
    print("GETTING CATEGORIES FROM URL "+url)
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, features="lxml")
    root_table = soup.find("table", class_=["navbox", "hlist"])
    sections = root_table.find_all("table", class_=["navbox", "hlist"])
    for section in sections:
        category_name = to_id(section.find("span", class_="navbox-title").text.strip())
        rows = section.find("tbody").find_all("tr", recursive=False)
        for row in rows:
            subcats = extract_names(row.find("th").text)
            for entry in row.find_all("li", recursive=True):
                entry_name = sanitize_name(entry.find("a").get("title"))
                # The * indicates that this item has variants, like color for example.
                # The plugin will use this data when deciding if an item matches the id
                entry_id = name_to_id_map.get(entry_name, "*"+to_id(entry_name))
                entry_categories = [category_name] + subcats
                add_categories_to_item(entry_id, entry_categories)
                print("  " + entry_name + " (" + entry_id +"): " + str(entry_categories))

def fetch_mobs():
    print("ADDING MOB DROP DATA TO ITEM CATEGORIES")
    response = requests.get(MOB_LIST_URL)
    html = response.text
    soup = BeautifulSoup(html, features="lxml")
    mob_links = soup.select('.mob-name > a')
    for link in mob_links:
        fetch_mob_drops("https://minecraft.wiki"+link.get("href"))

def fetch_mob_drops(mob_url: str):
    response = requests.get(mob_url)
    html = response.text
    soup = BeautifulSoup(html, features="lxml")
    mob_id_table = soup.find("table", class_="id-table")
    if mob_id_table:
        mob_id = mob_id_table.select_one("td > code").text
        drop_table = soup.find("div", class_="droptable-tabber")
        drop_ids = []
        if drop_table:
            drops = drop_table.select("td > a")        
            # print(drops)
            for drop in drops:
                drop_id = name_to_id_map.get(sanitize_name(drop.get("title")))
                if drop_id is not None and drop_id not in drop_ids:
                    drop_ids.append(drop_id)
        for drop in drop_ids:
            key = drop
            if drop not in id_to_categories_map:
                # This probably means you hit a variant (ex. blue_carpet) which won't be found
                # Set the key to the base item
                base_block = drop.split("_")
                key = "*"+base_block[len(base_block)-1]
            if key in id_to_categories_map:
                add_categories_to_item(key, [mob_id, "mob_drop"])
            else:
                print("    " + key + " not found in id_to_category_map!")
        print("  "+mob_id + ": "+str(drop_ids))

def fetch_dimension_blocks(url: str):
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, features="lxml")
    dim_id_table = soup.find("table", class_="id-table")
    if dim_id_table:
        dim_id = dim_id_table.select_one("td > code").text
        print(dim_id)
        links = soup.select(".div-col .sprite-text")
        for link in links:
            name = sanitize_name(link.text)
            if name in name_to_id_map:
                found_id = name_to_id_map[name]
                print("    "+name+ " >>> " + found_id)
                add_categories_to_item(found_id, [dim_id])


fetch_block_name_map()
fetch_item_name_map()
fetch_wiki_categories(BLOCK_CATEGORIES_URL)
fetch_wiki_categories(ITEM_CATEGORIES_URL)
fetch_mobs()
fetch_dimension_blocks(NETHER_URL)
fetch_dimension_blocks(END_URL)

with open("output.csv", "w", encoding="utf-8") as f:
    for k, v in sorted(id_to_categories_map.items()):
        f.write(",".join([k] + v)+"\n")
    f.close()