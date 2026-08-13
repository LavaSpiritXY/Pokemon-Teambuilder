import requests
import streamlit as strlit

from champions.constants import CUSTOM_MEGAS_DATA
from champions.move_data import display_name_for_move, get_champions_species_key
from champions.roster_data import get_clean_api_name, get_base_api_name
