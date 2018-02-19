# Craigslist Apartments Recipe ☮ 🛋

This repo provides a very basic demo recipe that retrieves items from 
a craigslist search results page creates a qri dataset according to 
the schema specified by the schema within `structure.json`. 


## Requiremnts

- qri 0.1.2 or later
  - get latest release [here](https://github.com/qri-io/qri/releases)
  - or [build from source](https://github.com/qri-io/qri#building-from-source)
- python 2.7

## Usage

1. clone the repo and cd to the project 
```
git clone https://github.com/qri-recipes/craigslist_apartments.git
cd craigslist_apartments
```
1. Install any missing python dependencies
```
pip install -r requirements.txt
```
2. execute script
```
python cl_apartment_recipe.py
```

## Customization

(TODO)
- change url/search page
- change number of pages
- adding fields to the schema
- reuse for different websites, new recipes