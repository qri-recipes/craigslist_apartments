from bs4 import BeautifulSoup
import requests
from collections import OrderedDict
import re
import datetime
import json
import os
import shlex
import sys
from subprocess import Popen, PIPE


NOW = datetime.datetime.now()
_MAX_ATTEMPTS = 10
_DELAY = .1
_TMP_PATH = "/tmp/qri/"

QRI_COMMAND_TEMPLATE="""qri {action} \
--data "{DATA_PATH}" \
--structure "{STRUCTURE_PATH}" \
--meta "{META_PATH}" \
me/{DATASET_NAME}
"""

# get variables from env
try:  
   DATASET_NAME   = os.environ["r_dataset_name"]
   TARGET_URL     = os.environ["r_target_url"]
   DATA_PATH      = os.environ["r_data_path"]
   STRUCTURE_PATH = os.environ["r_structure_path"]
   META_PATH      = os.environ["r_meta_path"]
   CITY_NAME      = os.environ["r_default_location"]
   NUM_PAGES      = int(os.environ["r_num_pages"])
   # test_run       = True if os.environ["r_test"] == "True" else False
except KeyError as e: 
   print "Please ensure all required environment variales are set: missing {}".format(e)
   sys.exit(1)

# data retrieval -----------------------------------------------------  

def fetch_page(url, query_params=""):
    page = requests.get(url=url, params=query_params)
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup

def get_page_items_from_class(page, name="", class_=""):
    kwargs = dict()
    if class_ != "":
        kwargs["class_"] = class_
    if name != "":
        kwargs["name"]=name
    results = page.find_all(**kwargs)
    return results

def parse_page_items(page_items, item_fields, page_num):
    """ Parse a list of items from a page

    Args:
        page_items (list): list of tags (type bs4.element.Tag) from a 
            page.
        item_fields (list): list of tuples containing the following
            information in order:
                - class name of the tag you want to locate
                - which attribute of the tag you want to keep - here,
                    we just consider inner text or href 
                - the name to store the field as
                - any post-processing function if applicable that
                    either takes a single input string as an argument 
                    or an input string plus additional arguments 
                    specified by the next argument
                - additional params (as a list) for the 
                    post-processing function
    """
    parsed_items = list()
    for page_item in page_items:
        output = OrderedDict()
        for class_name, method, save_name, process_func, func_params in item_fields:
            output[save_name] = None
            field = page_item.find(class_=class_name)
            if field:
                if method == "text":
                    output[save_name] = field.text
                if method == "href":
                    attrs = field.attrs
                    if "href" in attrs:
                        output[save_name] = attrs['href']
                if process_func != None:
                    if func_params != None:
                        output[save_name] = process_func(output[save_name], *func_params)
                    else:
                        output[save_name] = process_func(output[save_name])
        output[u"page_num"] = page_num
        parsed_items.append(output)
    return parsed_items


# post-processor functions--------------------------------------------

def price_as_number(s):
    p= re.compile("[^0-9.]")
    stripped = re.sub(pattern=p, repl="", string=s)
    if stripped != "":
        return float(stripped)

def string_as_date_string(s):
    default_year = NOW.year
    s = s + " {}".format(default_year)
    informat = "%b %d %Y"
    outformat = "%Y-%m-%d"
    try:
        date_val = datetime.datetime.strptime(s, informat)
        date_string = datetime.datetime.strftime(date_val, outformat)
        return date_string
    except:
        return None
# shell execution-----------------------------------------------------
def _shell_exec_once(command):
    proc = Popen(shlex.split(command), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdoutdata, err = proc.communicate()
    if err != "":
        raise Exception(err)
    return stdoutdata

def _shell_exec(command):
    stdoutdata = _shell_exec_once(command)
    for _ in range(_MAX_ATTEMPTS - 1):
        if "error" not in stdoutdata[:15]:
            break
        time.sleep(_DELAY)
        stdoutdata = _shell_exec_once(command)
    return stdoutdata

# --------------------------------------------------------------------
def _dataset_exists(DATASET_NAME):
    cmd = "qri info me/{} | grep ^error".format(DATASET_NAME)
    result = _shell_exec(cmd)
    if result == "":
        return True
    else:
        return False

def add_or_save_to_qri():
    action = "add"
    if _dataset_exists(DATASET_NAME):
        #add commit message and choose 'save'
        date_string = datetime.datetime.strftime(NOW, "%Y-%m-%dT%H:%M:%S")
        message = "recipe update @ {}".format(date_string)
        action = "save -m=\"{}\"".format(message)
    params = dict(
        action=action,
        DATA_PATH=DATA_PATH,
        STRUCTURE_PATH=STRUCTURE_PATH,
        META_PATH=META_PATH,
        DATASET_NAME=DATASET_NAME,
        )
    cmd = QRI_COMMAND_TEMPLATE.format(**params)
    result = _shell_exec(cmd)
    print(result)
    #print cmd

# --------------------------------------------------------------------

def main():
    # url
    url = TARGET_URL
    # fields and processing
    item_fields= [
        (u"result-title", u"text", u"title", None, None),
        (u"result-title", u"href", u"url", None, None),
        (u"result-price", u"text", u"price", price_as_number, None),
        (u"result-hood", u"text", u"neighborhood", None, None),
        (u"result-date", u"text", u"date", string_as_date_string, None),
    ]
    #item_element="li"
    item_class="result-row"

    # scrape the pages
    results = list()
    print("processing pages "),
    for i in range(NUM_PAGES):
        page_num = i + 1
        print("{},".format(page_num)),
        if i == 0:
            params = ""
        else:
            params = {"s": 120*i}
        page = fetch_page(url, params)
        page_items = get_page_items_from_class(page, class_=item_class)
        page_data = parse_page_items(page_items, item_fields, page_num)
        results += page_data

    #as json
    jsontable = list()
    for r in results:
        od = OrderedDict()
        od[u"name"] = r["title"]
        od[u"url"] = r["url"]
        loc = OrderedDict()
        loc["name"] = r["neighborhood"]
        loc["containedInPlace"] = {"name": CITY_NAME}
        od[u"containedIn"] = loc
        price = OrderedDict()
        price["name"] = "price"
        price["value"] = r["price"]
        price["currency"] = "USD"
        od[u"additionalProperty"] = price
        od[u"date"] = r["date"]
        jsontable.append(od)
    if os.path.exists(DATA_PATH):
        cmd = "mv {path} prev_{path}".format(path=DATA_PATH)
        _shell_exec(cmd)
    with open(DATA_PATH, "w") as fp:
        fp.write(json.dumps(jsontable, indent=2))
    # save to qri
    add_or_save_to_qri()



if __name__ == "__main__":
    main()

