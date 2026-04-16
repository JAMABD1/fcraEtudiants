from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from main.models import Etudiant, Orphelin, International, Universite, Archive
from .models import ChatConversation, ChatMessage
from .serializers import (
    EtudiantSerializer, OrphelinSerializer, InternationalSerializer,
    UniversiteSerializer,
    ChatConversationSerializer, ChatMessageSerializer
)
import google.generativeai as genai
from decouple import config
import requests
import datetime

# Configure Gemini
GEMINI_API_KEY = config('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

EXTERNAL_API_BASE = "http://102.16.39.246:11802"


def _unwrap_list_response(data):
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def _fix_nested_student_images(records, nested_key: str):
    if not isinstance(records, list):
        return
    avatar = f"{EXTERNAL_API_BASE}/media/images/avatar.jpg"
    for row in records:
        if not isinstance(row, dict):
            continue
        nested = row.get(nested_key)
        if not isinstance(nested, dict):
            continue
        ip = nested.get("imageprofile")
        if ip and not str(ip).startswith("http"):
            nested["imageprofile"] = EXTERNAL_API_BASE + str(ip)
        elif not ip:
            nested["imageprofile"] = avatar


def _sort_and_limit_list(items, order_by: str = None, limit: int = None):
    if not isinstance(items, list):
        return items
    if order_by:
        reverse = order_by.startswith("-")
        raw = order_by[1:] if reverse else order_by
        parts = raw.split("__")

        def _dig(d, path_parts):
            cur = d
            for p in path_parts:
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(p)
            return cur

        def _sort_key(x):
            v = _dig(x, parts) if isinstance(x, dict) else None
            return (v is None, v)

        items = list(items)
        items.sort(key=_sort_key, reverse=reverse)
    if limit is not None and isinstance(limit, int) and limit > 0:
        items = items[:limit]
    return items


def _normalize_pays(pays: str) -> str:
    key = pays.strip().lower().replace("é", "e")
    aliases = {
        "inde": "India",
        "india": "India",
        "irak": "Irak",
        "iraq": "Irak",
        "iran": "Iran",
        "maroc": "Maroc",
        "morocco": "Maroc",
        "indonesie": "Indonésie",
        "indonesia": "Indonésie",
        "france": "France",
        "autre": "Autre",
    }
    return aliases.get(key, pays)


def _normalize_genre_filter(genre: str) -> str:
    g = genre.lower().strip()
    return {
        "fille": "F",
        "femme": "F",
        "f": "F",
        "garçon": "M",
        "garcon": "M",
        "homme": "M",
        "m": "M",
    }.get(g, genre)


def _normalize_class_filter(Class: str) -> str:
    c = Class.lower().replace(" ", "")
    class_map = {
        "3eme": "3eme",
        "3ème": "3eme",
        "3è": "3eme",
        "4eme": "4eme",
        "4ème": "4eme",
        "4è": "4eme",
        "5eme": "5eme",
        "5ème": "5eme",
        "5è": "5eme",
        "6eme": "6eme",
        "6ème": "6eme",
        "6è": "6eme",
        "2nd": "2nd",
        "2nde": "2nd",
        "seconde": "2nd",
        "1ere": "1ere",
        "1ère": "1ere",
        "première": "1ere",
        "terminal": "Terminal",
        "terminale": "Terminal",
        "ps": "PS",
        "ms": "MS",
        "gs": "GS",
        "cp": "CP",
        "ce1": "CE1",
        "ce2": "CE2",
        "cm1": "CM1",
        "cm2": "CM2",
    }
    if "1ereannee" in c:
        return "1ere annee"
    if "2emeannee" in c:
        return "2eme annee"
    if "3emeannee" in c:
        return "3eme annee"
    if "4emeannee" in c:
        return "4eme annee"
    if "5emeannee" in c:
        return "5eme annee"
    if "6emeannee" in c:
        return "6eme annee"
    return class_map.get(c, Class)


def _normalize_designation_filter(designation: str) -> str:
    d = designation.lower()
    designation_map = {
        "université": "Universite",
        "universite": "Universite",
        "jeune": "Jeune",
        "elite": "Elite",
        "international": "International",
        "petit": "Petit",
        "crashcourse": "crashcourse",
        "internat": "internat",
        "dine": "dine",
        "bachelor dine": "Bachelor Dine",
        "bachelor université": "Bachelor Université",
    }
    return designation_map.get(d, designation)


def get_etudiants(identifiant: str = None, nom: str = None, genre: str = None, designation: str = None, institution: str = None, ville: str = None, Class: str = None, centre: str = None, status: str = None, telephone: str = None, nom_pere: str = None, nom_mere: str = None, telephone_mere: str = None, date_entre_after: str = None, date_entre_before: str = None, limit: int = None, order_by: str = None):
    """
    Récupère les informations sur les étudiants depuis l'API externe.
    Permet de filtrer par identifiant, nom, genre, désignation, institution, ville, classe, centre, statut, téléphone, parents ou date d'entrée.
    
    Arguments additionnels :
    - limit: Nombre maximum de résultats à retourner (ex: 5).
    - order_by: Champ de tri. Préfixer par '-' pour un tri descendant (ex: '-date_entre' pour les plus récents).
    
    Normalisation automatique des paramètres :
    - genre: 'fille', 'femme', 'F' -> 'F'; 'garçon', 'homme', 'M' -> 'M'
    - Class: '3ème', '3 ème', '3è' -> '3eme'; '2nde', '2nd' -> '2nd'; '1ère', '1ere' -> '1ere', etc.
    - designation: 'université' -> 'Universite', etc.
    """
    url = f"{EXTERNAL_API_BASE}/api/etudiants/"
    params = {}
    
    # Normalisation du genre
    if genre:
        genre_map = {
            'fille': 'F', 'femme': 'F', 'f': 'F',
            'garçon': 'M', 'garcon': 'M', 'homme': 'M', 'm': 'M'
        }
        genre = genre_map.get(genre.lower(), genre)
        params['genre'] = genre

    # Normalisation de la classe (Class)
    if Class:
        # Supprimer les espaces et mettre en minuscule
        c = Class.lower().replace(" ", "")
        class_map = {
            '3eme': '3eme', '3ème': '3eme', '3è': '3eme',
            '4eme': '4eme', '4ème': '4eme', '4è': '4eme',
            '5eme': '5eme', '5ème': '5eme', '5è': '5eme',
            '6eme': '6eme', '6ème': '6eme', '6è': '6eme',
            '2nd': '2nd', '2nde': '2nd', 'seconde': '2nd',
            '1ere': '1ere', '1ère': '1ere', 'première': '1ere',
            'terminal': 'Terminal', 'terminale': 'Terminal',
            'ps': 'PS', 'ms': 'MS', 'gs': 'GS', 'cp': 'CP',
            'ce1': 'CE1', 'ce2': 'CE2', 'cm1': 'CM1', 'cm2': 'CM2'
        }
        # Gérer aussi les années universitaires
        if '1ereannee' in c: Class = '1ere annee'
        elif '2emeannee' in c: Class = '2eme annee'
        elif '3emeannee' in c: Class = '3eme annee'
        elif '4emeannee' in c: Class = '4eme annee'
        elif '5emeannee' in c: Class = '5eme annee'
        elif '6emeannee' in c: Class = '6eme annee'
        else: Class = class_map.get(c, Class)
        params['Class'] = Class

    # Normalisation de la désignation
    if designation:
        d = designation.lower()
        designation_map = {
            'université': 'Universite', 'universite': 'Universite',
            'jeune': 'Jeune', 'elite': 'Elite', 'international': 'International',
            'petit': 'Petit', 'crashcourse': 'crashcourse', 'internat': 'internat',
            'dine': 'dine', 'bachelor dine': 'Bachelor Dine', 'bachelor université': 'Bachelor Université'
        }
        designation = designation_map.get(d, designation)
        params['designation'] = designation

    if identifiant: params['identifiant'] = identifiant
    if nom: params['nom__icontains'] = nom
    if institution: params['institution'] = institution
    if ville: params['ville'] = ville
    if centre: params['centre'] = centre
    if status: params['status'] = status
    if telephone: params['telephone'] = telephone
    if nom_pere: params['nom_pere__icontains'] = nom_pere
    if nom_mere: params['nom_mere__icontains'] = nom_mere
    if telephone_mere: params['telephone_mere'] = telephone_mere
    if date_entre_after: params['date_entre__gte'] = date_entre_after
    if date_entre_before: params['date_entre__lte'] = date_entre_before
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Ensure image URLs are absolute
        for student in data:
            if student.get('imageprofile'):
                if not student['imageprofile'].startswith('http'):
                    student['imageprofile'] = EXTERNAL_API_BASE + student['imageprofile']
            else:
                student['imageprofile'] = EXTERNAL_API_BASE + "/media/images/avatar.jpg"

        # Filtrage pour correspondre à l'interface principale (main.views)
        # On exclut par défaut les "Sortant" sauf si un statut spécifique est demandé
        # OU si on fait une recherche spécifique par nom ou identifiant
        if not status and not nom and not identifiant:
            data = [s for s in data if s.get('status') in ['Actif', 'Inactif']]
            
        # Tri manuel si demandé (car l'API externe peut ne pas le supporter directement)
        if order_by:
            reverse = order_by.startswith('-')
            key = order_by[1:] if reverse else order_by
            # On trie en gérant les valeurs None
            data.sort(key=lambda x: (x.get(key) is None, x.get(key)), reverse=reverse)

        # Limitation du nombre de résultats
        if limit and isinstance(limit, int):
            data = data[:limit]

        return data
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des étudiants: {str(e)}"}

def get_orphelins(nom: str = None, decede: str = None, centre: str = None, Class: str = None, genre: str = None, institution: str = None, age: str = None, acte_de_dece: str = None, fillier: str = None, limit: int = None, order_by: str = None):
    """
    Récupère les informations sur les orphelins depuis l'API externe.
    Permet de filtrer par nom, type de décès (decede: 'mère', 'père', 'Orphelin père et mère', 'non orphelin'), centre, classe (Class), genre (M/F), institution, âge (age: '3-10', '11-14', '15-18', '19-21', '22-25', '26+' OU formats flexibles: 'less_than_15', '10-15', 'greater_than_20'), documents (acte_de_dece: 'complete'/'incomplete') ou filière (fillier).
    
    Arguments additionnels :
    - limit: Nombre maximum de résultats à retourner.
    - order_by: Champ de tri. Préfixer par '-' pour un tri descendant.
    
    Normalisation automatique des paramètres :
    - genre: 'fille', 'femme', 'F' -> 'F'; 'garçon', 'homme', 'M' -> 'M'
    - Class: '3ème', '3 ème', '3è' -> '3eme', etc.
    - decede: 'mere' -> 'mère', 'pere' -> 'père', etc.
    """
    url = f"{EXTERNAL_API_BASE}/api/orphelins/"
    params = {}
    
    # Normalisation du genre
    if genre:
        genre_map = {'fille': 'F', 'femme': 'F', 'f': 'F', 'garçon': 'M', 'garcon': 'M', 'homme': 'M', 'm': 'M'}
        genre = genre_map.get(genre.lower(), genre)
        params['identifiant__genre'] = genre

    # Normalisation de la classe (Class)
    if Class:
        c = Class.lower().replace(" ", "")
        class_map = {
            '3eme': '3eme', '3ème': '3eme', '3è': '3eme',
            '4eme': '4eme', '4ème': '4eme', '4è': '4eme',
            '5eme': '5eme', '5ème': '5eme', '5è': '5eme',
            '6eme': '6eme', '6ème': '6eme', '6è': '6eme',
            '2nd': '2nd', '2nde': '2nd', 'seconde': '2nd',
            '1ere': '1ere', '1ère': '1ere', 'première': '1ere',
            'terminal': 'Terminal', 'terminale': 'Terminal',
            'ps': 'PS', 'ms': 'MS', 'gs': 'GS', 'cp': 'CP',
            'ce1': 'CE1', 'ce2': 'CE2', 'cm1': 'CM1', 'cm2': 'CM2'
        }
        Class = class_map.get(c, Class)
        params['identifiant__Class'] = Class

    # Normalisation du statut de décès
    if decede:
        d = decede.lower().replace(" ", "")
        decede_map = {
            'mere': 'mère', 'maman': 'mère',
            'pere': 'père', 'papa': 'père',
            'orphelinpereetmere': 'Orphelin père et mère', 'lesdeux': 'Orphelin père et mère',
            'nonorphelin': 'non orphelin', 'vivant': 'non orphelin'
        }
        decede = decede_map.get(d, decede)
        params['décedé'] = decede

    if nom: params['identifiant__nom__icontains'] = nom
    if centre: params['identifiant__centre'] = centre
    if institution: params['identifiant__institution'] = institution
    if age: params['age'] = age
    if acte_de_dece: params['acte_de_dece'] = acte_de_dece
    if fillier: params['identifiant__fillier'] = fillier
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Ensure image URLs are absolute
        for orphelin in data:
            if orphelin.get('identifiant') and orphelin['identifiant'].get('imageprofile'):
                if not orphelin['identifiant']['imageprofile'].startswith('http'):
                    orphelin['identifiant']['imageprofile'] = EXTERNAL_API_BASE + orphelin['identifiant']['imageprofile']
            elif orphelin.get('identifiant'):
                orphelin['identifiant']['imageprofile'] = EXTERNAL_API_BASE + "/media/images/avatar.jpg"
                
        # Tri manuel
        if order_by:
            reverse = order_by.startswith('-')
            key = order_by[1:] if reverse else order_by
            # Pour les orphelins, certains champs sont dans 'identifiant'
            def get_val(x, k):
                if k.startswith('identifiant__'):
                    sub_k = k.replace('identifiant__', '')
                    return x.get('identifiant', {}).get(sub_k)
                return x.get(k)
            data.sort(key=lambda x: (get_val(x, key) is None, get_val(x, key)), reverse=reverse)

        # Limitation
        if limit and isinstance(limit, int):
            data = data[:limit]

        return data
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des orphelins: {str(e)}"}

def get_internationaux(
    pays: str = None,
    nom: str = None,
    identifiant: str = None,
    genre: str = None,
    centre: str = None,
    institution: str = None,
    ville: str = None,
    Class: str = None,
    designation: str = None,
    telephone: str = None,
    status: str = None,
    nom_pere: str = None,
    nom_mere: str = None,
    telephone_mere: str = None,
    fillier: str = None,
    date_depart: str = None,
    date_depart_after: str = None,
    date_depart_before: str = None,
    duree_sejour: int = None,
    duree_sejour_min: int = None,
    duree_sejour_max: int = None,
    limit: int = None,
    order_by: str = None,
):
    """
    Récupère les étudiants internationaux depuis l'API externe (filtres type Django REST).

    Filtres étudiant (champs liés via international__) : nom, identifiant, genre, centre,
    institution, ville, classe (Class), désignation, téléphone, statut, parents, filière (fillier).
    Filtres spécifiques : pays, date_depart / date_depart_after / date_depart_before,
    duree_sejour ou plage duree_sejour_min / duree_sejour_max (années de séjour).
    Post-traitement : limit, order_by (ex. '-international__date_entre', 'pays').
    """
    url = f"{EXTERNAL_API_BASE}/api/international/"
    params = {}

    if pays:
        params["pays"] = _normalize_pays(pays)
    if nom:
        params["international__nom__icontains"] = nom
    if identifiant:
        params["international__identifiant"] = identifiant
    if genre:
        params["international__genre"] = _normalize_genre_filter(genre)
    if centre:
        params["international__centre"] = centre
    if institution:
        params["international__institution"] = institution
    if ville:
        params["international__ville"] = ville
    if Class:
        params["international__Class"] = _normalize_class_filter(Class)
    if designation:
        params["international__designation"] = _normalize_designation_filter(designation)
    if telephone:
        params["international__telephone"] = telephone
    if status:
        params["international__status"] = status
    if nom_pere:
        params["international__nom_pere__icontains"] = nom_pere
    if nom_mere:
        params["international__nom_mere__icontains"] = nom_mere
    if telephone_mere:
        params["international__telephone_mere"] = telephone_mere
    if fillier:
        params["international__fillier"] = fillier
    if date_depart:
        params["date_depart"] = date_depart
    if date_depart_after:
        params["date_depart__gte"] = date_depart_after
    if date_depart_before:
        params["date_depart__lte"] = date_depart_before
    if duree_sejour is not None:
        params["duree_sejour"] = duree_sejour
    if duree_sejour_min is not None:
        params["duree_sejour__gte"] = duree_sejour_min
    if duree_sejour_max is not None:
        params["duree_sejour__lte"] = duree_sejour_max

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = _unwrap_list_response(response.json())
        if isinstance(data, dict):
            return data
        if not isinstance(data, list):
            return []
        _fix_nested_student_images(data, "international")
        return _sort_and_limit_list(data, order_by=order_by, limit=limit)
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des internationaux: {str(e)}"}


def get_universites(
    email: str = None,
    email_icontains: str = None,
    nom: str = None,
    identifiant: str = None,
    genre: str = None,
    centre: str = None,
    institution: str = None,
    ville: str = None,
    Class: str = None,
    fillier: str = None,
    designation: str = None,
    telephone: str = None,
    status: str = None,
    nom_pere: str = None,
    nom_mere: str = None,
    telephone_mere: str = None,
    date_entre_after: str = None,
    date_entre_before: str = None,
    date_sortie_after: str = None,
    date_sortie_before: str = None,
    date_naissance_after: str = None,
    date_naissance_before: str = None,
    limit: int = None,
    order_by: str = None,
):
    """
    Récupère les fiches université depuis l'API externe.

    Filtre direct : email (exact), email_icontains.
    Filtres sur l'étudiant lié (universite__) : nom, identifiant, genre, centre, institution,
    ville, classe, filière, désignation, téléphone, statut, parents, dates d'entrée / sortie /
    naissance.
    Post-traitement : limit, order_by (ex. '-universite__date_entre', 'email').
    """
    url = f"{EXTERNAL_API_BASE}/api/universite/"
    params = {}

    if email:
        params["email"] = email
    if email_icontains:
        params["email__icontains"] = email_icontains
    if nom:
        params["universite__nom__icontains"] = nom
    if identifiant:
        params["universite__identifiant"] = identifiant
    if genre:
        params["universite__genre"] = _normalize_genre_filter(genre)
    if centre:
        params["universite__centre"] = centre
    if institution:
        params["universite__institution"] = institution
    if ville:
        params["universite__ville"] = ville
    if Class:
        params["universite__Class"] = _normalize_class_filter(Class)
    if fillier:
        params["universite__fillier"] = fillier
    if designation:
        params["universite__designation"] = _normalize_designation_filter(designation)
    if telephone:
        params["universite__telephone"] = telephone
    if status:
        params["universite__status"] = status
    if nom_pere:
        params["universite__nom_pere__icontains"] = nom_pere
    if nom_mere:
        params["universite__nom_mere__icontains"] = nom_mere
    if telephone_mere:
        params["universite__telephone_mere"] = telephone_mere
    if date_entre_after:
        params["universite__date_entre__gte"] = date_entre_after
    if date_entre_before:
        params["universite__date_entre__lte"] = date_entre_before
    if date_sortie_after:
        params["universite__date_sortie__gte"] = date_sortie_after
    if date_sortie_before:
        params["universite__date_sortie__lte"] = date_sortie_before
    if date_naissance_after:
        params["universite__date_naissance__gte"] = date_naissance_after
    if date_naissance_before:
        params["universite__date_naissance__lte"] = date_naissance_before

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = _unwrap_list_response(response.json())
        if isinstance(data, dict):
            return data
        if not isinstance(data, list):
            return []
        _fix_nested_student_images(data, "universite")
        return _sort_and_limit_list(data, order_by=order_by, limit=limit)
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des universités: {str(e)}"}

def calculate_age_distribution(birthdates, current_year):
    age_groups = {
        "3-10 ans": 0,
        "11-14 ans": 0,
        "15-18 ans": 0,
        "19-21 ans": 0,
        "22-25 ans": 0,
        "26+ ans": 0
    }
    for birthdate in birthdates:
        age = current_year - birthdate.year
        if 3 <= age <= 10:
            age_groups["3-10 ans"] += 1
        elif 11 <= age <= 14:
            age_groups["11-14 ans"] += 1
        elif 15 <= age <= 18:
            age_groups["15-18 ans"] += 1
        elif 19 <= age <= 21:
            age_groups["19-21 ans"] += 1
        elif 22 <= age <= 25:
            age_groups["22-25 ans"] += 1
        elif age >= 26:
            age_groups["26+ ans"] += 1
    return [{"age": group, "count": count} for group, count in age_groups.items()]

def get_statistics_etudiant(identifiant: str = None, nom: str = None, genre: str = None, designation: str = None, institution: str = None, ville: str = None, Class: str = None, centre: str = None, status: str = None, telephone: str = None, nom_pere: str = None, nom_mere: str = None, telephone_mere: str = None, date_entre_after: str = None, date_entre_before: str = None, age: str = None):
    """
    Calcul des statistiques pour les étudiants avec filtrage croisé complet.
    
    Paramètre age : 
    - Tranches fixes: '3-10', '11-14', '15-18', '19-21', '22-25', '26+'
    - Plage exacte: 'min-max' (ex: '10-15' pour les étudiants de 10 à 15 ans inclus).
    Utilisez la plage exacte pour répondre précisément à une demande d'âge spécifique.
    """
    archived_etudiant_ids = Archive.objects.values_list('archive_id', flat=True)
    # On filtre pour exclure les archivés ET les sortants pour correspondre à l'interface principale
    active_etudiants = Etudiant.objects.exclude(id__in=archived_etudiant_ids)
    
    if not status:
        active_etudiants = active_etudiants.filter(status__in=['Actif', 'Inactif'])
    else:
        active_etudiants = active_etudiants.filter(status=status)

    # Application de tous les filtres possibles (boosted filtering)
    if identifiant: active_etudiants = active_etudiants.filter(identifiant=identifiant)
    if nom: active_etudiants = active_etudiants.filter(nom__icontains=nom)
    if genre: active_etudiants = active_etudiants.filter(genre=genre)
    if designation: active_etudiants = active_etudiants.filter(designation=designation)
    if institution: active_etudiants = active_etudiants.filter(institution=institution)
    if ville: active_etudiants = active_etudiants.filter(ville=ville)
    if Class: active_etudiants = active_etudiants.filter(Class=Class)
    if centre: active_etudiants = active_etudiants.filter(centre=centre)
    if telephone: active_etudiants = active_etudiants.filter(telephone=telephone)
    if nom_pere: active_etudiants = active_etudiants.filter(nom_pere__icontains=nom_pere)
    if nom_mere: active_etudiants = active_etudiants.filter(nom_mere__icontains=nom_mere)
    if telephone_mere: active_etudiants = active_etudiants.filter(telephone_mere=telephone_mere)
    if date_entre_after: active_etudiants = active_etudiants.filter(date_entre__gte=date_entre_after)
    if date_entre_before: active_etudiants = active_etudiants.filter(date_entre__lte=date_entre_before)
    
    # Filtrage par âge complexe (tranches ou min-max)
    if age:
        from datetime import date
        current_year = date.today().year
        if age == '3-10':
            active_etudiants = active_etudiants.filter(date_naissance__year__gte=current_year-10, date_naissance__year__lte=current_year-3)
        elif age == '11-14':
            active_etudiants = active_etudiants.filter(date_naissance__year__gte=current_year-14, date_naissance__year__lte=current_year-11)
        elif age == '15-18':
            active_etudiants = active_etudiants.filter(date_naissance__year__gte=current_year-18, date_naissance__year__lte=current_year-15)
        elif age == '19-21':
            active_etudiants = active_etudiants.filter(date_naissance__year__gte=current_year-21, date_naissance__year__lte=current_year-19)
        elif age == '22-25':
            active_etudiants = active_etudiants.filter(date_naissance__year__gte=current_year-25, date_naissance__year__lte=current_year-22)
        elif age == '26+':
            active_etudiants = active_etudiants.filter(date_naissance__year__lte=current_year-26)
        elif '-' in age:
            try:
                start_age, end_age = map(int, age.split('-'))
                if start_age <= end_age:
                    active_etudiants = active_etudiants.filter(
                        date_naissance__year__gte=current_year - end_age,
                        date_naissance__year__lte=current_year - start_age,
                    )
            except ValueError:
                pass

    from datetime import datetime
    current_year = datetime.now().year
    
    if age:
        # Si un filtrage par âge est appliqué, on retourne cette plage spécifique
        par_age = [{"age": f"{age} ans", "count": active_etudiants.count()}]
    else:
        # Sinon, on utilise la distribution par tranches habituelle
        etudiants_with_birthdate = active_etudiants.exclude(date_naissance__isnull=True).values_list('date_naissance', flat=True)
        par_age = calculate_age_distribution(etudiants_with_birthdate, current_year)

    return {
        'total': active_etudiants.count(),
        'par_genre': list(active_etudiants.values('genre').annotate(count=Count('genre'))),
        'par_status': list(active_etudiants.values('status').annotate(count=Count('status'))),
        'par_classe': list(active_etudiants.values('Class').annotate(count=Count('Class'))),
        'par_centre': list(active_etudiants.values('centre').annotate(count=Count('centre'))),
        'par_designation': list(active_etudiants.values('designation').annotate(count=Count('designation'))),
        'par_institution': list(active_etudiants.values('institution').annotate(count=Count('institution'))),
        'par_ville': list(active_etudiants.values('ville').annotate(count=Count('ville'))),
        'par_age': par_age,
    }

def get_statistics_orphelin(nom: str = None, decede: str = None, centre: str = None, Class: str = None, genre: str = None, institution: str = None, age: str = None, acte_de_dece: str = None, fillier: str = None, **kwargs):
    """
    Calcul des statistiques pour les orphelins avec filtrage croisé.
    
    Paramètre age : 
    - Tranches fixes: '3-10', '11-14', '15-18', '19-21', '22-25', '26+'
    - Plage exacte: 'min-max' (ex: '10-15' pour les orphelins de 10 à 15 ans inclus).
    Utilisez la plage exacte pour répondre précisément à une demande d'âge spécifique.
    """
    archived_etudiant_ids = Archive.objects.values_list('archive_id', flat=True)
    active_orphelins = Orphelin.objects.exclude(identifiant_id__in=archived_etudiant_ids)
    
    # Application des filtres
    if nom: active_orphelins = active_orphelins.filter(identifiant__nom__icontains=nom)
    if decede: active_orphelins = active_orphelins.filter(décedé=decede)
    if centre: active_orphelins = active_orphelins.filter(identifiant__centre=centre)
    if Class: active_orphelins = active_orphelins.filter(identifiant__Class=Class)
    if genre: active_orphelins = active_orphelins.filter(identifiant__genre=genre)
    if institution: active_orphelins = active_orphelins.filter(identifiant__institution=institution)
    if fillier: active_orphelins = active_orphelins.filter(identifiant__fillier=fillier)
    
    # Filtrage par âge complexe (tranches)
    if age:
        from datetime import date
        current_year = date.today().year
        if age == '3-10':
            active_orphelins = active_orphelins.filter(identifiant__date_naissance__year__gte=current_year-10, identifiant__date_naissance__year__lte=current_year-3)
        elif age == '11-14':
            active_orphelins = active_orphelins.filter(identifiant__date_naissance__year__gte=current_year-14, identifiant__date_naissance__year__lte=current_year-11)
        elif age == '15-18':
            active_orphelins = active_orphelins.filter(identifiant__date_naissance__year__gte=current_year-18, identifiant__date_naissance__year__lte=current_year-15)
        elif age == '19-21':
            active_orphelins = active_orphelins.filter(identifiant__date_naissance__year__gte=current_year-21, identifiant__date_naissance__year__lte=current_year-19)
        elif age == '22-25':
            active_orphelins = active_orphelins.filter(identifiant__date_naissance__year__gte=current_year-25, identifiant__date_naissance__year__lte=current_year-22)
        elif age == '26+':
            active_orphelins = active_orphelins.filter(identifiant__date_naissance__year__lte=current_year-26)
        elif '-' in age:
            try:
                start_age, end_age = map(int, age.split('-'))
                if start_age <= end_age:
                    active_orphelins = active_orphelins.filter(
                        identifiant__date_naissance__year__gte=current_year - end_age,
                        identifiant__date_naissance__year__lte=current_year - start_age,
                    )
            except ValueError:
                pass

    if acte_de_dece:
        if acte_de_dece == 'complete':
            active_orphelins = active_orphelins.exclude(acte_de_décé='')
        elif acte_de_dece == 'incomplete':
            active_orphelins = active_orphelins.filter(acte_de_décé='')

    from datetime import datetime
    current_year = datetime.now().year
    
    if age:
        # Si un filtrage par âge est appliqué, on retourne cette plage spécifique
        par_age_orphelins = [{"age": f"{age} ans", "count": active_orphelins.count()}]
    else:
        # Sinon, on utilise la distribution par tranches habituelle
        orphelins_with_birthdate = active_orphelins.exclude(identifiant__date_naissance__isnull=True).values_list('identifiant__date_naissance', flat=True)
        par_age_orphelins = calculate_age_distribution(orphelins_with_birthdate, current_year)

    return {
        'total': active_orphelins.count(),
        'decedes': active_orphelins.filter(décedé__in=["mère", "père", "Orphelin père et mère"]).count(),
        'vivants': active_orphelins.filter(décedé="non orphelin").count(),
        'par_centre': list(active_orphelins.values('identifiant__centre').annotate(count=Count('identifiant__centre')).order_by('-count')),
        'par_genre': list(active_orphelins.values('identifiant__genre').annotate(count=Count('identifiant__genre')).order_by('-count')),
        'par_age': par_age_orphelins,
        'par_classe': list(active_orphelins.values('identifiant__Class').annotate(count=Count('identifiant__Class')).order_by('-count')),
        'par_fillier': list(active_orphelins.values('identifiant__fillier').annotate(count=Count('identifiant__fillier')).order_by('-count')),
        'par_institution': list(active_orphelins.values('identifiant__institution').annotate(count=Count('identifiant__institution')).order_by('-count')),
        'par_designation': list(active_orphelins.values('identifiant__designation').annotate(count=Count('identifiant__designation')).order_by('-count')),
        'par_ville': list(active_orphelins.values('identifiant__ville').annotate(count=Count('identifiant__ville')).order_by('-count')),
        'par_decede': list(active_orphelins.values('décedé').annotate(count=Count('décedé')).order_by('-count')),
    }


def _apply_age_filter_on_queryset(qs, age: str, birthdate_field: str):
    """Filtrage par âge sur un champ date de naissance (notation ORM, ex. 'international__date_naissance')."""
    if not age:
        return qs
    from datetime import date

    current_year = date.today().year
    if age == "3-10":
        return qs.filter(
            **{f"{birthdate_field}__year__gte": current_year - 10, f"{birthdate_field}__year__lte": current_year - 3}
        )
    if age == "11-14":
        return qs.filter(
            **{f"{birthdate_field}__year__gte": current_year - 14, f"{birthdate_field}__year__lte": current_year - 11}
        )
    if age == "15-18":
        return qs.filter(
            **{f"{birthdate_field}__year__gte": current_year - 18, f"{birthdate_field}__year__lte": current_year - 15}
        )
    if age == "19-21":
        return qs.filter(
            **{f"{birthdate_field}__year__gte": current_year - 21, f"{birthdate_field}__year__lte": current_year - 19}
        )
    if age == "22-25":
        return qs.filter(
            **{f"{birthdate_field}__year__gte": current_year - 25, f"{birthdate_field}__year__lte": current_year - 22}
        )
    if age == "26+":
        return qs.filter(**{f"{birthdate_field}__year__lte": current_year - 26})
    if "-" in age:
        try:
            start_age, end_age = map(int, age.split("-"))
            if start_age <= end_age:
                return qs.filter(
                    **{
                        f"{birthdate_field}__year__gte": current_year - end_age,
                        f"{birthdate_field}__year__lte": current_year - start_age,
                    }
                )
        except ValueError:
            pass
    return qs


def get_statistics_international(
    pays: str = None,
    nom: str = None,
    identifiant: str = None,
    genre: str = None,
    centre: str = None,
    institution: str = None,
    ville: str = None,
    Class: str = None,
    designation: str = None,
    status: str = None,
    fillier: str = None,
    date_depart_after: str = None,
    date_depart_before: str = None,
    duree_sejour_min: int = None,
    duree_sejour_max: int = None,
    age: str = None,
    **kwargs,
):
    """
    Statistiques sur les étudiants internationaux (hors archives), avec filtres croisés.

    Paramètre age : tranches '3-10', '11-14', … '26+' ou plage 'min-max' (ex. '10-15').
    """
    archived_etudiant_ids = Archive.objects.values_list("archive_id", flat=True)
    qs = International.objects.exclude(international_id__in=archived_etudiant_ids)

    if pays:
        qs = qs.filter(pays=_normalize_pays(pays))
    if nom:
        qs = qs.filter(international__nom__icontains=nom)
    if identifiant:
        qs = qs.filter(international__identifiant=identifiant)
    if genre:
        qs = qs.filter(international__genre=_normalize_genre_filter(genre))
    if centre:
        qs = qs.filter(international__centre=centre)
    if institution:
        qs = qs.filter(international__institution=institution)
    if ville:
        qs = qs.filter(international__ville=ville)
    if Class:
        qs = qs.filter(international__Class=_normalize_class_filter(Class))
    if designation:
        qs = qs.filter(international__designation=_normalize_designation_filter(designation))
    if status:
        qs = qs.filter(international__status=status)
    if fillier:
        qs = qs.filter(international__fillier=fillier)
    if date_depart_after:
        qs = qs.filter(date_depart__gte=date_depart_after)
    if date_depart_before:
        qs = qs.filter(date_depart__lte=date_depart_before)
    if duree_sejour_min is not None:
        qs = qs.filter(duree_sejour__gte=duree_sejour_min)
    if duree_sejour_max is not None:
        qs = qs.filter(duree_sejour__lte=duree_sejour_max)

    birth_field = "international__date_naissance"
    qs = _apply_age_filter_on_queryset(qs, age, birth_field)

    from datetime import datetime

    current_year = datetime.now().year

    if age:
        par_age = [{"age": f"{age} ans", "count": qs.count()}]
    else:
        birthdates = qs.exclude(international__date_naissance__isnull=True).values_list(
            "international__date_naissance", flat=True
        )
        par_age = calculate_age_distribution(birthdates, current_year)

    return {
        "total": qs.count(),
        "avec_date_depart": qs.exclude(date_depart__isnull=True).count(),
        "sans_date_depart": qs.filter(date_depart__isnull=True).count(),
        "par_pays": list(qs.values("pays").annotate(count=Count("pays")).order_by("-count")),
        "par_genre": list(
            qs.values("international__genre").annotate(count=Count("international__genre")).order_by("-count")
        ),
        "par_status": list(
            qs.values("international__status").annotate(count=Count("international__status")).order_by("-count")
        ),
        "par_centre": list(
            qs.values("international__centre").annotate(count=Count("international__centre")).order_by("-count")
        ),
        "par_classe": list(
            qs.values("international__Class").annotate(count=Count("international__Class")).order_by("-count")
        ),
        "par_fillier": list(
            qs.values("international__fillier").annotate(count=Count("international__fillier")).order_by("-count")
        ),
        "par_institution": list(
            qs.values("international__institution")
            .annotate(count=Count("international__institution"))
            .order_by("-count")
        ),
        "par_designation": list(
            qs.values("international__designation")
            .annotate(count=Count("international__designation"))
            .order_by("-count")
        ),
        "par_ville": list(
            qs.values("international__ville").annotate(count=Count("international__ville")).order_by("-count")
        ),
        "par_duree_sejour": list(
            qs.values("duree_sejour").annotate(count=Count("id")).order_by("-count")
        ),
        "par_age": par_age,
    }


def get_statistics_universite(
    email: str = None,
    email_icontains: str = None,
    nom: str = None,
    identifiant: str = None,
    genre: str = None,
    centre: str = None,
    institution: str = None,
    ville: str = None,
    Class: str = None,
    fillier: str = None,
    designation: str = None,
    status: str = None,
    date_entre_after: str = None,
    date_entre_before: str = None,
    date_sortie_after: str = None,
    date_sortie_before: str = None,
    age: str = None,
    **kwargs,
):
    """
    Statistiques sur les fiches université (hors archives), avec filtres croisés sur l'étudiant lié.

    Paramètre age : tranches ou plage 'min-max' sur la date de naissance de l'étudiant.
    """
    archived_etudiant_ids = Archive.objects.values_list("archive_id", flat=True)
    qs = Universite.objects.exclude(universite_id__in=archived_etudiant_ids)

    if email:
        qs = qs.filter(email=email)
    if email_icontains:
        qs = qs.filter(email__icontains=email_icontains)
    if nom:
        qs = qs.filter(universite__nom__icontains=nom)
    if identifiant:
        qs = qs.filter(universite__identifiant=identifiant)
    if genre:
        qs = qs.filter(universite__genre=_normalize_genre_filter(genre))
    if centre:
        qs = qs.filter(universite__centre=centre)
    if institution:
        qs = qs.filter(universite__institution=institution)
    if ville:
        qs = qs.filter(universite__ville=ville)
    if Class:
        qs = qs.filter(universite__Class=_normalize_class_filter(Class))
    if fillier:
        qs = qs.filter(universite__fillier=fillier)
    if designation:
        qs = qs.filter(universite__designation=_normalize_designation_filter(designation))
    if status:
        qs = qs.filter(universite__status=status)
    if date_entre_after:
        qs = qs.filter(universite__date_entre__gte=date_entre_after)
    if date_entre_before:
        qs = qs.filter(universite__date_entre__lte=date_entre_before)
    if date_sortie_after:
        qs = qs.filter(universite__date_sortie__gte=date_sortie_after)
    if date_sortie_before:
        qs = qs.filter(universite__date_sortie__lte=date_sortie_before)

    birth_field = "universite__date_naissance"
    qs = _apply_age_filter_on_queryset(qs, age, birth_field)

    from datetime import datetime

    current_year = datetime.now().year

    if age:
        par_age = [{"age": f"{age} ans", "count": qs.count()}]
    else:
        birthdates = qs.exclude(universite__date_naissance__isnull=True).values_list(
            "universite__date_naissance", flat=True
        )
        par_age = calculate_age_distribution(birthdates, current_year)

    with_email = qs.exclude(Q(email__isnull=True) | Q(email=""))

    return {
        "total": qs.count(),
        "avec_email": with_email.count(),
        "sans_email": qs.count() - with_email.count(),
        "par_genre": list(
            qs.values("universite__genre").annotate(count=Count("universite__genre")).order_by("-count")
        ),
        "par_status": list(
            qs.values("universite__status").annotate(count=Count("universite__status")).order_by("-count")
        ),
        "par_centre": list(
            qs.values("universite__centre").annotate(count=Count("universite__centre")).order_by("-count")
        ),
        "par_classe": list(
            qs.values("universite__Class").annotate(count=Count("universite__Class")).order_by("-count")
        ),
        "par_fillier": list(
            qs.values("universite__fillier").annotate(count=Count("universite__fillier")).order_by("-count")
        ),
        "par_institution": list(
            qs.values("universite__institution")
            .annotate(count=Count("universite__institution"))
            .order_by("-count")
        ),
        "par_designation": list(
            qs.values("universite__designation")
            .annotate(count=Count("universite__designation"))
            .order_by("-count")
        ),
        "par_ville": list(
            qs.values("universite__ville").annotate(count=Count("universite__ville")).order_by("-count")
        ),
        "par_age": par_age,
    }


def get_statistics(category: str = None, **kwargs):
    """
    Calcule des statistiques globales avec support du filtrage croisé complet.
    Exemple: get_statistics(category='etudiants', centre='Andakana', genre='F')
    """
    stats = {}
    
    if category in ['etudiants', 'sortants', 'all', None]:
        # On ne passe que les kwargs valides pour les étudiants
        etudiant_kwargs = {k: v for k, v in kwargs.items() if k in ['identifiant', 'nom', 'genre', 'designation', 'institution', 'ville', 'Class', 'centre', 'status', 'telephone', 'nom_pere', 'nom_mere', 'telephone_mere', 'date_entre_after', 'date_entre_before', 'age']}
        stats['etudiants'] = get_statistics_etudiant(**etudiant_kwargs)
        
    if category in ['orphelins', 'all', None]:
        # On ne passe que les kwargs valides pour les orphelins
        orphelin_kwargs = {k: v for k, v in kwargs.items() if k in ['nom', 'decede', 'centre', 'Class', 'genre', 'institution', 'age', 'acte_de_dece', 'fillier']}
        stats['orphelins'] = get_statistics_orphelin(**orphelin_kwargs)

    if category in ['internationaux', 'international', 'all', None]:
        intl_keys = [
            'pays', 'nom', 'identifiant', 'genre', 'centre', 'institution', 'ville', 'Class',
            'designation', 'status', 'fillier', 'date_depart_after', 'date_depart_before',
            'duree_sejour_min', 'duree_sejour_max', 'age',
        ]
        intl_kwargs = {k: v for k, v in kwargs.items() if k in intl_keys}
        stats['internationaux'] = get_statistics_international(**intl_kwargs)

    if category in ['universites', 'universite', 'université', 'all', None]:
        uni_keys = [
            'email', 'email_icontains', 'nom', 'identifiant', 'genre', 'centre', 'institution',
            'ville', 'Class', 'fillier', 'designation', 'status', 'date_entre_after',
            'date_entre_before', 'date_sortie_after', 'date_sortie_before', 'age',
        ]
        uni_kwargs = {k: v for k, v in kwargs.items() if k in uni_keys}
        stats['universites'] = get_statistics_universite(**uni_kwargs)

    return stats

model = genai.GenerativeModel('gemini-2.5-flash',
 tools=[
     get_etudiants, get_orphelins, get_internationaux,
     get_universites, get_statistics,
     get_statistics_etudiant, get_statistics_orphelin,
     get_statistics_international, get_statistics_universite,
 ],
   system_instruction="""Tu es un assistant de chatbot expert pour le système FCRA. Ta mission est d'analyser les données des étudiants et de fournir des rapports détaillés.

PROCESSUS DE RÉPONSE OBLIGATOIRE :
1. ANALYSE : Identifie ce que l'utilisateur demande (statistiques, recherche d'un étudiant, limitation aux X premiers/derniers, etc.).
2. APPEL D'OUTILS : Tu DOIS TOUJOURS appeler un outil (ex: 'get_statistics_etudiant', 'get_etudiants') avant de répondre.
   - Pour "les 5 derniers", utilise 'limit=5' et 'order_by="-date_entre"' (ou le champ de date approprié).
   - Pour "les 5 premiers", utilise 'limit=5' et 'order_by="date_entre"'.
3. VÉRIFICATION : Si l'outil retourne des données, procède à la réponse. Si l'outil retourne une erreur ou est vide, explique-le précisément.
4. RÉPONSE TEXTUELLE : Fournis d'abord une analyse textuelle complète et détaillée des données reçues.
5. GRAPHIQUES (Si applicable) : Si tu présentes des statistiques, génère un graphique Chart.js APRÈS le texte.

Outils disponibles :
- 'get_etudiants', 'get_orphelins' : Recherche détaillée. Supportent désormais 'limit' (int) et 'order_by' (str, ex: '-date_entre', 'nom').
- 'get_internationaux' : Filtres pays, nom/identifiant étudiant, genre, centre, institution, ville, Class, désignation, statut, parents, fillier, dates de départ, durée de séjour (duree_sejour ou min/max), limit, order_by (ex. '-international__date_entre').
- 'get_universites' : Filtres email (exact ou email_icontains), champs étudiant universite__ (nom, identifiant, genre, centre, institution, ville, Class, fillier, désignation, téléphone, statut, parents), dates entrée/sortie/naissance, limit, order_by.
- 'get_statistics' : Statistiques globales. Utilise category ('etudiants', 'sortants', 'orphelins', 'internationaux', 'international', 'universites', 'universite', 'all' ou None) + filtres croisés.
- 'get_statistics_etudiant' : Statistiques spécifiques pour les étudiants. Supporte TOUS les filtres. Paramètre age : tranches fixes (3-10, 11-14, …) ou plage exacte 'min-max' (ex. 5 à 10 ans → age='5-10').
- 'get_statistics_orphelin' : Statistiques pour les orphelins. Retourne total, decedes, vivants, par_age, par_centre, par_genre, par_classe, par_fillier, par_institution, par_designation, par_ville, par_decede. Paramètre age : tranches fixes (3-10, 11-14, …) ou plage exacte 'min-max' (ex. 5 à 10 ans → age='5-10').
- 'get_statistics_international' : Statistiques internationaux (total, par_pays, par_genre, par_centre, par_classe, par_fillier, par_institution, par_designation, par_ville, par_status, par_duree_sejour, par_age, avec/sans date_depart). Filtres : pays, nom, identifiant, genre, centre, institution, ville, Class, designation, status, fillier, dates départ, duree_sejour min/max, age.
- 'get_statistics_universite' : Statistiques université (total, avec_email/sans_email, par_genre, par_status, par_centre, par_classe, par_fillier, par_institution, par_designation, par_ville, par_age). Filtres : email, email_icontains, nom, identifiant, genre, centre, institution, ville, Class, fillier, designation, status, dates entrée/sortie, age.

CONSIGNES CRUCIALES :
- Catégories autorisées : Étudiants, Sortants, Orphelins, Universités, Internationaux.
- Précision de l'âge : Si l'utilisateur demande un âge ou une plage précise (ex: "10 à 15 ans"), tu DOIS impérativement passer l'argument 'age' (ex: age='10-15') à l'outil de statistiques. Ne te contente pas de regarder la distribution par tranches par défaut.
- Interdiction de calcul manuel : Ne calcule JAMAIS manuellement un total en additionnant les tranches d'âge (ex: 3-10 + 11-14) si une plage exacte peut être demandée via l'outil.
- Limitation et Tri : Si l'utilisateur demande un nombre précis (ex: "les 5 derniers"), utilise impérativement les paramètres 'limit' et 'order_by' dans ton appel d'outil.
- L'âge d'un étudiant : Calcule-le (Année actuelle - Année de naissance).
- Images : Affiche TOUJOURS ![Nom](URL) au début pour les recherches individuelles ou les listes courtes.
- Accord de genre : Utilise le féminin pour 'F' et le masculin pour 'M'.
- Graphiques : Utilise ce format JSON exact dans un bloc ```json :
   ```json
   {
     "type": "pie" | "bar" | "doughnut",
     "data": {
       "labels": ["Label 1", "Label 2"],
       "datasets": [{
         "label": "Titre",
         "data": [10, 20],
         "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40"]
       }]
     },
     "options": { "responsive": true, "maintainAspectRatio": false }
   }
   ```
- INTERDICTION : Ne génère JAMAIS de blocs JSON vides comme {} ou des messages disant "pas de données" sans avoir réellement appelé l'outil de statistiques correspondant."""
 )

class EtudiantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Etudiant.objects.all()
    serializer_class = EtudiantSerializer
    lookup_field = 'identifiant'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        'nom': ['exact', 'icontains'],
        'identifiant': ['exact'],
        'genre': ['exact'],
        'designation': ['exact'],
        'institution': ['exact'],
        'ville': ['exact'],
        'Class': ['exact'],
        'centre': ['exact'],
        'status': ['exact'],
        'telephone': ['exact'],
        'nom_pere': ['exact', 'icontains'],
        'nom_mere': ['exact', 'icontains'],
        'telephone_mere': ['exact'],
        'date_entre': ['exact', 'gte', 'lte'],
    }
    search_fields = ['nom']

class OrphelinViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Orphelin.objects.all()
    serializer_class = OrphelinSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        'décedé': ['exact'],
        'identifiant__nom': ['exact', 'icontains'],
        'identifiant__centre': ['exact'],
        'identifiant__Class': ['exact'],
        'identifiant__genre': ['exact'],
        'identifiant__institution': ['exact'],
        'identifiant__fillier': ['exact'],
    }
    search_fields = ['identifiant__nom']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrage par âge (tranches ou formats flexibles)
        age_range = self.request.query_params.get('age')
        if age_range:
            current_year = datetime.date.today().year
            if age_range == '3-10':
                queryset = queryset.filter(identifiant__date_naissance__year__gte=current_year-10, identifiant__date_naissance__year__lte=current_year-3)
            elif age_range == '11-14':
                queryset = queryset.filter(identifiant__date_naissance__year__gte=current_year-14, identifiant__date_naissance__year__lte=current_year-11)
            elif age_range == '15-18':
                queryset = queryset.filter(identifiant__date_naissance__year__gte=current_year-18, identifiant__date_naissance__year__lte=current_year-15)
            elif age_range == '19-21':
                queryset = queryset.filter(identifiant__date_naissance__year__gte=current_year-21, identifiant__date_naissance__year__lte=current_year-19)
            elif age_range == '22-25':
                queryset = queryset.filter(identifiant__date_naissance__year__gte=current_year-25, identifiant__date_naissance__year__lte=current_year-22)
            elif age_range == '26+':
                queryset = queryset.filter(identifiant__date_naissance__year__lte=current_year-26)
            elif age_range.startswith('less_than_'):
                try:
                    age = int(age_range.split('_')[-1])
                    queryset = queryset.filter(identifiant__date_naissance__year__gte=current_year - age)
                except (ValueError, IndexError):
                    pass
            elif age_range.startswith('greater_than_'):
                try:
                    age = int(age_range.split('_')[-1])
                    queryset = queryset.filter(identifiant__date_naissance__year__lte=current_year - age)
                except (ValueError, IndexError):
                    pass
            elif '-' in age_range:
                try:
                    start, end = map(int, age_range.split('-'))
                    queryset = queryset.filter(identifiant__date_naissance__year__gte=current_year - end, identifiant__date_naissance__year__lte=current_year - start)
                except ValueError:
                    pass

        # Filtrage par complétude des documents (acte de décès)
        docs_completeness = self.request.query_params.get('acte_de_dece')
        if docs_completeness:
            if docs_completeness == 'complete':
                queryset = queryset.exclude(acte_de_décé='')
            elif docs_completeness == 'incomplete':
                queryset = queryset.filter(acte_de_décé='')

        return queryset

class InternationalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = International.objects.all()
    serializer_class = InternationalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        'pays': ['exact', 'icontains'],
        'date_depart': ['exact', 'gte', 'lte'],
        'duree_sejour': ['exact', 'gte', 'lte'],
        'international__identifiant': ['exact'],
        'international__nom': ['exact', 'icontains'],
        'international__genre': ['exact'],
        'international__centre': ['exact'],
        'international__institution': ['exact'],
        'international__ville': ['exact'],
        'international__Class': ['exact'],
        'international__designation': ['exact'],
        'international__fillier': ['exact'],
        'international__status': ['exact'],
        'international__telephone': ['exact'],
    }
    search_fields = ['international__nom', 'international__identifiant']

class UniversiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Universite.objects.all()
    serializer_class = UniversiteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        'email': ['exact', 'icontains'],
        'universite__identifiant': ['exact'],
        'universite__nom': ['exact'],
        'universite__genre': ['exact'],
        'universite__centre': ['exact'],
        'universite__institution': ['exact'],
        'universite__ville': ['exact'],
        'universite__Class': ['exact'],
        'universite__fillier': ['exact'],
        'universite__designation': ['exact'],
        'universite__status': ['exact'],
        'universite__telephone': ['exact'],
        'universite__date_entre': ['exact', 'gte', 'lte'],
        'universite__date_sortie': ['exact', 'gte', 'lte'],
        'universite__date_naissance': ['exact', 'gte', 'lte'],
    }
    search_fields = ['email', 'universite__nom', 'universite__identifiant']

def chatbot_view(request):
    """
    Renders the chatbot interface without the sidebar.
    """
    return render(request, 'api/chatbot.html', {'hide_sidebar': True})

from django.http import StreamingHttpResponse
import json

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chatbot_api(request):
    """
    API endpoint to handle chatbot messages using Gemini.
    Saves messages to a conversation and maintains history for memory.
    """
    message_text = request.data.get('message')
    conversation_id = request.data.get('conversation_id')
    
    if not message_text:
        return Response({'error': 'Message est requis'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Récupérer ou créer la conversation
    history = []
    if conversation_id:
        conversation = get_object_or_404(ChatConversation, id=conversation_id, user=request.user)
        # Récupérer l'historique des messages pour la mémoire
        previous_messages = conversation.messages.all().order_by('timestamp')
        for msg in previous_messages:
            history.append({
                "role": "user" if msg.is_user else "model",
                "parts": [msg.content],
            })
    else:
        # Créer une nouvelle conversation si aucune n'est fournie
        # Utiliser les 30 premiers caractères du message comme titre
        title = message_text[:30] + "..." if len(message_text) > 30 else message_text
        conversation = ChatConversation.objects.create(user=request.user, title=title)
    
    # Sauvegarder le message de l'utilisateur
    ChatMessage.objects.create(conversation=conversation, is_user=True, content=message_text)
    
    # Récupérer la date du jour pour aider Gemini dans ses calculs (ex: âge)
    today = datetime.date.today()
    current_date_str = today.strftime("%d/%m/%Y")
    
    # Ajouter le contexte de la date au message envoyé à Gemini
    full_message = f"[Date d'aujourd'hui: {current_date_str}]\n{message_text}"
    
    try:
        # Démarrer une session de chat avec l'historique pour la mémoire
        # enable_automatic_function_calling=True permet à Gemini d'appeler les outils automatiquement
        chat_session = model.start_chat(history=history, enable_automatic_function_calling=True)
        response = chat_session.send_message(full_message)
        reply_text = response.text
        
        # Sauvegarder la réponse de l'IA
        ChatMessage.objects.create(conversation=conversation, is_user=False, content=reply_text)
        
        return Response({
            'reply': reply_text,
            'conversation_id': conversation.id,
            'conversation_title': conversation.title
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_conversations(request):
    conversations = ChatConversation.objects.filter(user=request.user)
    serializer = ChatConversationSerializer(conversations, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_history(request, conversation_id):
    conversation = get_object_or_404(ChatConversation, id=conversation_id, user=request.user)
    messages = conversation.messages.all()
    serializer = ChatMessageSerializer(messages, many=True)
    return Response({
        'title': conversation.title,
        'messages': serializer.data
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_conversation(request, conversation_id):
    conversation = get_object_or_404(ChatConversation, id=conversation_id, user=request.user)
    conversation.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_all_conversations(request):
    ChatConversation.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
