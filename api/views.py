from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from main.models import Etudiant, Orphelin, International, Universite, Elite, Jamat, Archive, ArchiveJamat
from .models import ChatConversation, ChatMessage
from .serializers import (
    EtudiantSerializer, OrphelinSerializer, InternationalSerializer,
    UniversiteSerializer, EliteSerializer, JamatSerializer,
    ChatConversationSerializer, ChatMessageSerializer
)
import google.generativeai as genai
from decouple import config
import requests
import datetime

# Configure Gemini
GEMINI_API_KEY = config('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

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
    url = "http://102.16.39.246:11802/api/etudiants/"
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
        
        # Base URL for images from the external API
        base_image_url = "http://102.16.39.246:11802"
        
        # Ensure image URLs are absolute
        for student in data:
            if student.get('imageprofile'):
                if not student['imageprofile'].startswith('http'):
                    student['imageprofile'] = base_image_url + student['imageprofile']
            else:
                student['imageprofile'] = base_image_url + "/media/images/avatar.jpg"

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
    url = "http://102.16.39.246:11802/api/orphelins/"
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
        
        # Base URL for images from the external API
        base_image_url = "http://102.16.39.246:11802"
        
        # Ensure image URLs are absolute
        for orphelin in data:
            if orphelin.get('identifiant') and orphelin['identifiant'].get('imageprofile'):
                if not orphelin['identifiant']['imageprofile'].startswith('http'):
                    orphelin['identifiant']['imageprofile'] = base_image_url + orphelin['identifiant']['imageprofile']
            elif orphelin.get('identifiant'):
                orphelin['identifiant']['imageprofile'] = base_image_url + "/media/images/avatar.jpg"
                
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

def get_jamats(nom: str = None, centre: str = None, genre: str = None, age: int = None, conversion_year: int = None, adress: str = None, travail: str = None, limit: int = None, order_by: str = None):
    """
    Récupère les informations sur les membres du Jamat depuis l'API externe.
    Permet de filtrer par nom, centre, genre, âge, année de conversion, adresse ou travail.
    
    Arguments additionnels :
    - limit: Nombre maximum de résultats à retourner.
    - order_by: Champ de tri. Préfixer par '-' pour un tri descendant.
    
    Normalisation automatique des paramètres :
    - genre: 'fille', 'femme', 'F' -> 'F'; 'garçon', 'homme', 'M' -> 'M'
    """
    url = "http://102.16.39.246:11802/api/jamat/"
    params = {}
    
    # Normalisation du genre
    if genre:
        genre_map = {'fille': 'F', 'femme': 'F', 'f': 'F', 'garçon': 'M', 'garcon': 'M', 'homme': 'M', 'm': 'M'}
        genre = genre_map.get(genre.lower(), genre)
        params['genre'] = genre

    if nom: params['nom__icontains'] = nom
    if centre: params['centre'] = centre
    if age: params['age'] = age
    if conversion_year: params['conversion_year'] = conversion_year
    if adress: params['adress__icontains'] = adress
    if travail: params['travail__icontains'] = travail
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Base URL for images from the external API
        base_image_url = "http://102.16.39.246:11802"
        
        # Ensure image URLs are absolute
        for member in data:
            if member.get('imageprofile'):
                if not member['imageprofile'].startswith('http'):
                    member['imageprofile'] = base_image_url + member['imageprofile']
            else:
                member['imageprofile'] = base_image_url + "/media/images/avatar.jpg"
                
        # Tri manuel
        if order_by:
            reverse = order_by.startswith('-')
            key = order_by[1:] if reverse else order_by
            data.sort(key=lambda x: (x.get(key) is None, x.get(key)), reverse=reverse)

        # Limitation
        if limit and isinstance(limit, int):
            data = data[:limit]

        return data
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des jamats: {str(e)}"}


def get_internationaux(pays: str = None):
    """
    Récupère les informations sur les étudiants internationaux depuis l'API externe.
    """
    url = "http://102.16.39.246:11802/api/international/"
    params = {}
    if pays: params['pays'] = pays
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des internationaux: {str(e)}"}

def get_universites(email: str = None):
    """
    Récupère les informations sur les universités depuis l'API externe.
    """
    url = "http://102.16.39.246:11802/api/universite/"
    params = {}
    if email: params['email'] = email
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des universités: {str(e)}"}

def get_elites():
    """
    Récupère les informations sur les élites depuis l'API externe.
    """
    url = "http://102.16.39.246:11802/api/elites/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des élites: {str(e)}"}

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

def calculate_age_distribution_from_ages(ages):
    age_groups = {
        "3-10 ans": 0,
        "11-14 ans": 0,
        "15-18 ans": 0,
        "19-21 ans": 0,
        "22-25 ans": 0,
        "26+ ans": 0
    }
    for age in ages:
        if age is None: continue
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

def get_statistics_etudiant(identifiant: str = None, nom: str = None, genre: str = None, designation: str = None, institution: str = None, ville: str = None, Class: str = None, centre: str = None, status: str = None, telephone: str = None, nom_pere: str = None, nom_mere: str = None, telephone_mere: str = None, date_entre_after: str = None, date_entre_before: str = None):
    """Calcul des statistiques pour les étudiants avec filtrage croisé complet."""
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
    
    from datetime import datetime
    current_year = datetime.now().year
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

def get_statistics_orphelin(nom: str = None, decede: str = None, centre: str = None, Class: str = None, genre: str = None, institution: str = None, age: str = None, acte_de_dece: str = None, fillier: str = None):
    """Calcul des statistiques pour les orphelins avec filtrage croisé."""
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

    if acte_de_dece:
        if acte_de_dece == 'complete':
            active_orphelins = active_orphelins.exclude(acte_de_décé='')
        elif acte_de_dece == 'incomplete':
            active_orphelins = active_orphelins.filter(acte_de_décé='')

    from datetime import datetime
    current_year = datetime.now().year
    orphelins_with_birthdate = active_orphelins.exclude(identifiant__date_naissance__isnull=True).values_list('identifiant__date_naissance', flat=True)
    par_age_orphelins = calculate_age_distribution(orphelins_with_birthdate, current_year)

    return {
        'total': active_orphelins.count(),
        'decedes': active_orphelins.filter(décedé__in=["mère", "père", "Orphelin père et mère"]).count(),
        'vivants': active_orphelins.filter(décedé="non orphelin").count(),
        'par_centre': list(active_orphelins.values('identifiant__centre').annotate(count=Count('identifiant__centre'))),
        'par_genre': list(active_orphelins.values('identifiant__genre').annotate(count=Count('identifiant__genre'))),
        'par_age': par_age_orphelins,
    }

def get_statistics_jamat(nom: str = None, centre: str = None, genre: str = None, age: int = None, conversion_year: int = None, adress: str = None, travail: str = None):
    """Calcul des statistiques pour les membres du Jamat avec filtrage croisé."""
    archived_jamat_ids = ArchiveJamat.objects.values_list('jamat_id', flat=True)
    active_jamats = Jamat.objects.exclude(id__in=archived_jamat_ids)
    
    if nom: active_jamats = active_jamats.filter(nom__icontains=nom)
    if centre: active_jamats = active_jamats.filter(centre=centre)
    if genre: active_jamats = active_jamats.filter(genre=genre)
    if age: active_jamats = active_jamats.filter(age=age)
    if conversion_year: active_jamats = active_jamats.filter(conversion_year=conversion_year)
    if adress: active_jamats = active_jamats.filter(adress__icontains=adress)
    if travail: active_jamats = active_jamats.filter(travail__icontains=travail)

    jamats_ages = active_jamats.values_list('age', flat=True)
    par_age_jamats = calculate_age_distribution_from_ages(jamats_ages)
    
    return {
        'total': active_jamats.count(),
        'par_genre': list(active_jamats.values('genre').annotate(count=Count('genre'))),
        'par_centre': list(active_jamats.values('centre').annotate(count=Count('centre'))),
        'par_travail': list(active_jamats.values('travail').annotate(count=Count('travail'))),
        'par_age': par_age_jamats,
        'par_annee_conversion': list(active_jamats.values('conversion_year').annotate(count=Count('conversion_year'))),
        'par_adresse': list(active_jamats.values('adress').annotate(count=Count('adress'))),
    }

def get_statistics(category: str = None, **kwargs):
    """
    Calcule des statistiques globales avec support du filtrage croisé complet.
    Exemple: get_statistics(category='etudiants', centre='Andakana', genre='F')
    """
    stats = {}
    
    if category in ['etudiants', 'all', None]:
        stats['etudiants'] = get_statistics_etudiant(**kwargs)
        
    if category in ['orphelins', 'all', None]:
        # On ne passe que les kwargs valides pour les orphelins
        orphelin_kwargs = {k: v for k, v in kwargs.items() if k in ['nom', 'decede', 'centre', 'Class', 'genre', 'institution', 'age', 'acte_de_dece', 'fillier']}
        stats['orphelins'] = get_statistics_orphelin(**orphelin_kwargs)

    if category in ['jamats', 'all', None]:
        # On ne passe que les kwargs valides pour les jamats
        jamat_kwargs = {k: v for k, v in kwargs.items() if k in ['nom', 'centre', 'genre', 'age', 'conversion_year', 'adress', 'travail']}
        stats['jamats'] = get_statistics_jamat(**jamat_kwargs)
        
    return stats

model = genai.GenerativeModel('gemini-2.0-flash',
 tools=[
     get_etudiants, get_orphelins, get_jamats, get_internationaux, 
     get_universites, get_elites, get_statistics,
     get_statistics_etudiant, get_statistics_orphelin, 
     get_statistics_jamat
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
- 'get_etudiants', 'get_orphelins', 'get_jamats' : Recherche détaillée. Supportent désormais 'limit' (int) et 'order_by' (str, ex: '-date_entre', 'nom').
- 'get_internationaux', 'get_universites', 'get_elites' : Recherche spécifique.
- 'get_statistics' : Statistiques globales. Supporte le filtrage croisé via des arguments.
- 'get_statistics_etudiant' : Statistiques spécifiques pour les étudiants. Supporte TOUS les filtres.
- 'get_statistics_orphelin' : Statistiques pour les orphelins.
- 'get_statistics_jamat' : Statistiques pour les jamats.

CONSIGNES CRUCIALES :
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
        'pays': ['exact'],
        'international__nom': ['exact', 'icontains'],
    }
    search_fields = ['international__nom']

class UniversiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Universite.objects.all()
    serializer_class = UniversiteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['email']

class EliteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Elite.objects.all()
    serializer_class = EliteSerializer

class JamatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Jamat.objects.all()
    serializer_class = JamatSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        'nom': ['exact', 'icontains'],
        'jamatid': ['exact'],
        'genre': ['exact'],
        'age': ['exact'],
        'centre': ['exact'],
        'conversion_year': ['exact'],
        'adress': ['exact', 'icontains'],
        'travail': ['exact', 'icontains'],
    }
    search_fields = ['nom']

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
