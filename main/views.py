from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from .models import Etudiant,Personnel,Jamat,ArchiveJamat,Madrassah,ArchiveMadrassah,Avertissement,Presence,ImageUpload,DossierUpload,Profile,Orphelin,NoteEtudiant,Pension,DossierPension,Paiementpension,Cimitiere,DossierCimitiere,Archive,Elite,NoteElite,Conge,DossierPersonnel
from django.http import JsonResponse
from .models import Elite,NoteElite,HistoriqueEtudiant,Universite,Sortant,International, get_center_filter_values
from django.db.models import Q,Count,Avg,Sum
from django.contrib import messages
from django.contrib.auth  import authenticate,login as auth_login,logout
from django.contrib.auth.models import Group, User
import os
from django.conf import settings
from .decorators import unauthentificated_user,allowed_permisstion
from django.contrib.auth  import authenticate,login as auth_login,logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from collections import Counter
from datetime import date
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
import tempfile
from pathlib import Path
from django.contrib.staticfiles import finders
from django.views.generic import DetailView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import logging
from django.utils.http import urlencode
from datetime import datetime
from .form import LoginForm, SignUpForm


import os
from io import BytesIO
import requests

def takeinfoUser(response):
     cureentuser=response.user
     user_id=cureentuser.id

     profile=list(Profile.objects.filter(user_id=user_id).values())
     username=User.objects.get(id=user_id)
     
     return {"profile":profile,"username":username}

@unauthentificated_user
def loginSingup(request):
    login_form = LoginForm()
    
    if request.method == "POST":
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    
    context = {
        'login_form': login_form
    }
    return render(request, "main/loginSingup.html", context)

def singin(response):
    if response.method=="POST":
        username = response.POST.get("username")
        email = response.POST.get("email")
        password1 = response.POST.get("password1")
        password2 = response.POST.get("password2")
        
        if password1 != password2:
            messages.error(response, "Les mots de passe ne correspondent pas.")
        else:
            try:
                user = User.objects.create_user(username=username, email=email, password=password1)
                group = Group.objects.get(name='Basics')
                user.groups.add(group)
                messages.success(response, "Compte créé avec succès!")
                return redirect('loginSingup')
            except Exception as e:
                messages.error(response, "Erreur lors de la création du compte.")

    return render(response,"main/singin.html")

def logoutUser(response):
    logout(response)
    return redirect('loginSingup')
    
@login_required(login_url='loginSingup')    
def orphelin_dashboard(response):
    """
    Dedicated Orphelin dashboard view with comprehensive statistics and filtering
    """
    # User profile information
    userprofile = takeinfoUser(response)
    username = userprofile["username"]
    profileuser = userprofile["profile"]
    
    # Get filter parameters
    centre_filter = response.GET.get('centre', '')
    age_filter = response.GET.get('age', '')
    status_filter = response.GET.get('status', '')
    institution_filter = response.GET.get('institution', '')
    year_filter = response.GET.get('year', '')
    
    # === ORPHAN STATISTICS (Main Focus) ===
    orphan_student_ids = Orphelin.objects.values_list('identifiant__id', flat=True)
    orphelins_queryset = Orphelin.objects.all()
    
    # Apply filters to orphans
    if centre_filter:
        centre_values = get_center_filter_values(centre_filter)
        if centre_values:
            orphelins_queryset = orphelins_queryset.filter(identifiant__centre__in=centre_values)
        else:
            orphelins_queryset = orphelins_queryset.filter(identifiant__centre=centre_filter)
    if status_filter:
        orphelins_queryset = orphelins_queryset.filter(décedé=status_filter)
    if institution_filter:
        orphelins_queryset = orphelins_queryset.filter(identifiant__institution=institution_filter)
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            orphelins_queryset = orphelins_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            orphelins_queryset = orphelins_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            orphelins_queryset = orphelins_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            orphelins_queryset = orphelins_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            orphelins_queryset = orphelins_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            orphelins_queryset = orphelins_queryset.filter(identifiant__date_naissance__lte=end_date)
    
    total_orphans = orphelins_queryset.count()
    
    # Orphan Gender distribution (filtered)
    orphan_gender_stats = orphelins_queryset.values('identifiant__genre').annotate(count=Count('identifiant__genre'))
    
    # Orphan Age distribution (filtered)
    orphan_age_groups = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}
    for orphelin in orphelins_queryset:
        if orphelin.identifiant and orphelin.identifiant.date_naissance:
            today = date.today()
            age = today.year - orphelin.identifiant.date_naissance.year - ((today.month, today.day) < (orphelin.identifiant.date_naissance.month, orphelin.identifiant.date_naissance.day))
            if 3 <= age <= 10:
                orphan_age_groups['3-10'] += 1
            elif 11 <= age <= 14:
                orphan_age_groups['11-14'] += 1
            elif 15 <= age <= 18:
                orphan_age_groups['15-18'] += 1
            elif 19 <= age <= 21:
                orphan_age_groups['19-21'] += 1
            elif 22 <= age <= 25:
                orphan_age_groups['22-25'] += 1
            else:
                orphan_age_groups['26+'] += 1
    
    # Orphan Status distribution (filtered)
    orphan_decede_stats = orphelins_queryset.values('décedé').annotate(count=Count('décedé')).order_by('-count')
    
    # Orphan Center distribution (filtered)
    orphan_center_stats = orphelins_queryset.values('identifiant__centre').annotate(count=Count('identifiant__centre')).order_by('-count')
    
    # Orphan Institution distribution (filtered)
    orphan_institution_stats = orphelins_queryset.values('identifiant__institution').annotate(count=Count('identifiant__institution')).order_by('-count')
    
    # Orphan Class distribution (filtered)
    orphan_class_stats = orphelins_queryset.values('identifiant__Class').annotate(count=Count('identifiant__Class')).order_by('-count')
    
    # Document completeness statistics (filtered)
    orphelins_with_docs = orphelins_queryset.annotate(docs_count=Count('identifiant__dossier', distinct=True))
    
    doc_complete_count = 0
    doc_incomplete_count = 0
    doc_na_count = 0
    
    for orphelin in orphelins_with_docs:
        if orphelin.décedé == 'non orphelin':
            if orphelin.docs_count >= 3:
                doc_complete_count += 1
            else:
                doc_na_count += 1
        elif orphelin.décedé == 'père':
            if orphelin.acte_de_décé:
                doc_complete_count += 1
            else:
                doc_incomplete_count += 1
        else:  # mère, Orphelin père et mère
            if orphelin.docs_count >= 3:
                doc_complete_count += 1
            else:
                doc_incomplete_count += 1
    
    # === ORPHAN NOTES STATISTICS ===
    orphan_notes = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids)
    
    # Apply same filters to notes
    if centre_filter:
        centre_values = get_center_filter_values(centre_filter)
        if centre_values:
            orphan_notes = orphan_notes.filter(identifiant__centre__in=centre_values)
        else:
            orphan_notes = orphan_notes.filter(identifiant__centre=centre_filter)
    if institution_filter:
        orphan_notes = orphan_notes.filter(identifiant__institution=institution_filter)
    if year_filter:
        orphan_notes = orphan_notes.filter(annee=year_filter)
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            orphan_notes = orphan_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            orphan_notes = orphan_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            orphan_notes = orphan_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            orphan_notes = orphan_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            orphan_notes = orphan_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            orphan_notes = orphan_notes.filter(identifiant__date_naissance__lte=end_date)
    
    total_orphan_notes = orphan_notes.count()
    orphan_avg_score = orphan_notes.aggregate(Avg('moyen'))['moyen__avg'] or 0
    orphan_pass_rate = (orphan_notes.filter(moyen__gte=10).count() / total_orphan_notes * 100) if total_orphan_notes > 0 else 0
    orphan_excellence_rate = (orphan_notes.filter(moyen__gte=16).count() / total_orphan_notes * 100) if total_orphan_notes > 0 else 0
    
    # Orphan Grade ranges
    orphan_grade_ranges = {
        '0-8': orphan_notes.filter(moyen__lt=8).count(),
        '8-10': orphan_notes.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': orphan_notes.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': orphan_notes.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': orphan_notes.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': orphan_notes.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': orphan_notes.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # Orphan Decision statistics
    orphan_decision_stats = orphan_notes.values('decision').annotate(count=Count('decision')).order_by('-count')
    
    # Top performing orphans
    top_orphan_performers = orphan_notes.order_by('-moyen')[:10]
    
    # Filter options for dropdowns
    centres = Orphelin.objects.values_list('identifiant__centre', flat=True).distinct().exclude(identifiant__centre__isnull=True)
    institutions = Orphelin.objects.values_list('identifiant__institution', flat=True).distinct().exclude(identifiant__institution__isnull=True)
    statuses = Orphelin.objects.values_list('décedé', flat=True).distinct().exclude(décedé__isnull=True)
    years = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids).values_list('annee', flat=True).distinct().exclude(annee__isnull=True).order_by('-annee')
    
    context = {
        "username": username,
        "profile": profileuser,
        
        # Filter parameters
        'centre_filter': centre_filter,
        'age_filter': age_filter,
        'status_filter': status_filter,
        'institution_filter': institution_filter,
        'year_filter': year_filter,
        
        # Filter options
        'centres': list(centres),
        'institutions': list(institutions),
        'statuses': list(statuses),
        'years': list(years),
        
        # Orphan statistics
        'total_orphans': total_orphans,
        'orphan_gender_stats': orphan_gender_stats,
        'orphan_age_groups': orphan_age_groups,
        'orphan_decede_stats': orphan_decede_stats,
        'orphan_center_stats': orphan_center_stats,
        'orphan_institution_stats': orphan_institution_stats,
        'orphan_class_stats': orphan_class_stats,
        
        # Orphan notes statistics
        'total_orphan_notes': total_orphan_notes,
        'orphan_avg_score': round(orphan_avg_score, 2),
        'orphan_pass_rate': round(orphan_pass_rate, 1),
        'orphan_excellence_rate': round(orphan_excellence_rate, 1),
        'orphan_grade_ranges': orphan_grade_ranges,
        'orphan_decision_stats': orphan_decision_stats,
        'top_orphan_performers': top_orphan_performers,
        
        # Document statistics
        'with_documents': doc_complete_count,
        'without_documents': doc_incomplete_count,
        'document_percentage': round((doc_complete_count / total_orphans * 100) if total_orphans > 0 else 0, 1),
    }
    
    return render(response, "main/orphelin_dashboard.html", context)

@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def jamat_dashboard(request):
    """
    Dedicated Jamat dashboard view with statistics and filtering
    """
    userprofile = takeinfoUser(request)
    username = userprofile["username"]
    profileuser = userprofile["profile"]

    centre_filter = request.GET.get('centre', '')
    age_filter = request.GET.get('age', '')
    genre_filter = request.GET.get('genre', '')
    travail_filter = request.GET.get('travail', '')
    adress_filter = request.GET.get('adress', '')
    conversion_year_filter = request.GET.get('conversion_year', '')

    jamats_queryset = Jamat.objects.all()

    if centre_filter:
        jamats_queryset = jamats_queryset.filter(centre=centre_filter)
    if genre_filter:
        jamats_queryset = jamats_queryset.filter(genre=genre_filter)
    if travail_filter:
        jamats_queryset = jamats_queryset.filter(travail=travail_filter)
    if adress_filter:
        jamats_queryset = jamats_queryset.filter(adress=adress_filter)
    if conversion_year_filter:
        jamats_queryset = jamats_queryset.filter(conversion_year=conversion_year_filter)
    if age_filter:
        if age_filter == '-25':
            jamats_queryset = jamats_queryset.filter(age__lt=25)
        elif age_filter == '25-35':
            jamats_queryset = jamats_queryset.filter(age__gte=25, age__lte=35)
        elif age_filter == '36-50':
            jamats_queryset = jamats_queryset.filter(age__gte=36, age__lte=50)
        elif age_filter == '51+':
            jamats_queryset = jamats_queryset.filter(age__gt=50)

    total_jamats = jamats_queryset.count()

    # Gender stats (filtered)
    male_count = jamats_queryset.filter(genre='M').count()
    female_count = jamats_queryset.filter(genre='F').count()
    male_percentage = round((male_count / total_jamats * 100), 1) if total_jamats > 0 else 0
    female_percentage = round((female_count / total_jamats * 100), 1) if total_jamats > 0 else 0

    # Contact stats (filtered)
    with_contact = jamats_queryset.filter(telephone__isnull=False).exclude(telephone='').count()
    contact_percentage = round((with_contact / total_jamats * 100), 1) if total_jamats > 0 else 0

    # Age groups (filtered)
    jamat_age_groups = {'-25': 0, '25-35': 0, '36-50': 0, '51+': 0}
    for jamat in jamats_queryset:
        age = jamat.age
        if age < 25:
            jamat_age_groups['-25'] += 1
        elif 25 <= age <= 35:
            jamat_age_groups['25-35'] += 1
        elif 36 <= age <= 50:
            jamat_age_groups['36-50'] += 1
        else:
            jamat_age_groups['51+'] += 1

    # Distribution stats (filtered)
    jamat_gender_stats = jamats_queryset.values('genre').annotate(count=Count('genre'))
    jamat_center_stats = jamats_queryset.values('centre').annotate(count=Count('centre')).order_by('-count')
    jamat_work_stats = jamats_queryset.values('travail').annotate(count=Count('travail')).order_by('-count')
    jamat_location_stats = jamats_queryset.values('adress').annotate(count=Count('adress')).order_by('-count')
    jamat_conversion_stats = jamats_queryset.values('conversion_year').annotate(count=Count('conversion_year')).order_by('-count')

    centres = Jamat.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True).exclude(centre='')
    travails = Jamat.objects.values_list('travail', flat=True).distinct().exclude(travail__isnull=True).exclude(travail='')
    adresses = Jamat.objects.values_list('adress', flat=True).distinct().exclude(adress__isnull=True).exclude(adress='')
    conversion_years = Jamat.objects.values_list('conversion_year', flat=True).distinct().exclude(conversion_year__isnull=True)

    context = {
        "username": username,
        "profile": profileuser,
        'centre_filter': centre_filter,
        'age_filter': age_filter,
        'genre_filter': genre_filter,
        'travail_filter': travail_filter,
        'adress_filter': adress_filter,
        'conversion_year_filter': conversion_year_filter,
        'centres': list(centres),
        'travails': list(travails),
        'adresses': list(adresses),
        'conversion_years': list(conversion_years),
        'total_jamats': total_jamats,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'with_contact': with_contact,
        'contact_percentage': contact_percentage,
        'jamat_age_groups': jamat_age_groups,
        'jamat_gender_stats': jamat_gender_stats,
        'jamat_center_stats': jamat_center_stats,
        'jamat_work_stats': jamat_work_stats,
        'jamat_location_stats': jamat_location_stats,
        'jamat_conversion_stats': jamat_conversion_stats,
    }

    return render(request, "main/jamat_dashboard.html", context)


def _madrassah_age_bucket(age_str):
    if age_str is None or (isinstance(age_str, str) and not str(age_str).strip()):
        return 'Inconnu'
    s = str(age_str).lower().replace(' ans', '').strip()
    try:
        ai = int(float(s))
        if ai < 12:
            return '-12'
        if ai <= 16:
            return '12-16'
        if ai <= 20:
            return '17-20'
        return '21+'
    except (ValueError, TypeError):
        return 'Autre'


@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def madrassah_dashboard(request):
    """Tableau de bord Madrassah — statistiques et filtres (aligné sur jamat_dashboard)."""
    userprofile = takeinfoUser(request)
    username = userprofile["username"]
    profileuser = userprofile["profile"]

    centre_filter = request.GET.get('centre', '')
    age_filter = request.GET.get('age', '')
    genre_filter = request.GET.get('genre', '')
    class_filter = request.GET.get('class_madressah', '')

    qs = Madrassah.objects.all()
    if centre_filter:
        qs = qs.filter(centre=centre_filter)
    if genre_filter:
        qs = qs.filter(genre=genre_filter)
    if class_filter:
        qs = qs.filter(class_madressah=class_filter)
    if age_filter:
        if age_filter == '-12':
            qs = qs.filter(age__in=['5', '6', '7', '8', '9', '10', '11', '12'])
        elif age_filter == '12-16':
            qs = qs.filter(age__in=['12', '13', '14', '15', '16'])
        elif age_filter == '17-20':
            qs = qs.filter(age__in=['17', '18', '19', '20'])
        elif age_filter == '21+':
            age_values = [str(i) for i in range(21, 100)]
            qs = qs.filter(age__in=age_values)

    total_madrassahs = qs.count()
    male_count = qs.filter(genre='M').count()
    female_count = qs.filter(genre='F').count()
    male_percentage = round((male_count / total_madrassahs * 100), 1) if total_madrassahs > 0 else 0
    female_percentage = round((female_count / total_madrassahs * 100), 1) if total_madrassahs > 0 else 0
    with_parent = qs.exclude(parent__isnull=True).exclude(parent='').count()
    parent_percentage = round((with_parent / total_madrassahs * 100), 1) if total_madrassahs > 0 else 0

    madrassah_age_groups = {'-12': 0, '12-16': 0, '17-20': 0, '21+': 0, 'Inconnu': 0, 'Autre': 0}
    for m in qs:
        bucket = _madrassah_age_bucket(m.age)
        if bucket not in madrassah_age_groups:
            madrassah_age_groups['Autre'] = madrassah_age_groups.get('Autre', 0) + 1
        else:
            madrassah_age_groups[bucket] += 1

    madrassah_gender_stats = qs.values('genre').annotate(count=Count('genre'))
    madrassah_center_stats = qs.values('centre').annotate(count=Count('centre')).order_by('-count')
    madrassah_class_stats = (
        qs.exclude(class_madressah__isnull=True)
        .exclude(class_madressah='')
        .values('class_madressah')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    centres = Madrassah.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True).exclude(centre='')
    classes_madressah = (
        Madrassah.objects.values_list('class_madressah', flat=True)
        .distinct()
        .exclude(class_madressah__isnull=True)
        .exclude(class_madressah='')
    )

    context = {
        'username': username,
        'profile': profileuser,
        'centre_filter': centre_filter,
        'age_filter': age_filter,
        'genre_filter': genre_filter,
        'class_filter': class_filter,
        'centres': list(centres),
        'classes_madressah': list(classes_madressah),
        'total_madrassahs': total_madrassahs,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'with_parent': with_parent,
        'parent_percentage': parent_percentage,
        'madrassah_age_groups': madrassah_age_groups,
        'madrassah_gender_stats': madrassah_gender_stats,
        'madrassah_center_stats': madrassah_center_stats,
        'madrassah_class_stats': madrassah_class_stats,
    }
    return render(request, 'main/madrassah_dashboard.html', context)


@login_required(login_url='loginSingup')
def elite_dashboard(response):
    """
    Dedicated Elite dashboard view with comprehensive statistics and filtering
    """
    # User profile information
    userprofile = takeinfoUser(response)
    username = userprofile["username"]
    profileuser = userprofile["profile"]
    
    # Get filter parameters
    centre_filter = response.GET.get('centre', '')
    age_filter = response.GET.get('age', '')
    institution_filter = response.GET.get('institution', '')
    year_filter = response.GET.get('year', '')
    
    # === ELITE STATISTICS (Main Focus) ===
    elite_student_ids = Elite.objects.values_list('identifiant__id', flat=True)
    elites_queryset = Elite.objects.all()
    
    # Apply filters to elites
    if centre_filter:
        elites_queryset = elites_queryset.filter(identifiant__centre=centre_filter)
    if institution_filter:
        elites_queryset = elites_queryset.filter(identifiant__institution=institution_filter)
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            elites_queryset = elites_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            elites_queryset = elites_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            elites_queryset = elites_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            elites_queryset = elites_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            elites_queryset = elites_queryset.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            elites_queryset = elites_queryset.filter(identifiant__date_naissance__lte=end_date)
    
    total_elites = elites_queryset.count()
    archived_elites_total = Archive.objects.filter(archive_type='Elite').count()
    
    # Elite Gender distribution (filtered)
    elite_gender_stats = elites_queryset.values('identifiant__genre').annotate(count=Count('identifiant__genre'))
    
    # Elite Age distribution (filtered)
    elite_age_groups = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}
    for elite in elites_queryset:
        if elite.identifiant and elite.identifiant.date_naissance:
            today = date.today()
            age = today.year - elite.identifiant.date_naissance.year - ((today.month, today.day) < (elite.identifiant.date_naissance.month, elite.identifiant.date_naissance.day))
            if 3 <= age <= 10:
                elite_age_groups['3-10'] += 1
            elif 11 <= age <= 14:
                elite_age_groups['11-14'] += 1
            elif 15 <= age <= 18:
                elite_age_groups['15-18'] += 1
            elif 19 <= age <= 21:
                elite_age_groups['19-21'] += 1
            elif 22 <= age <= 25:
                elite_age_groups['22-25'] += 1
            else:
                elite_age_groups['26+'] += 1
    
    # Elite Center distribution (filtered)
    elite_center_stats = elites_queryset.values('identifiant__centre').annotate(count=Count('identifiant__centre')).order_by('-count')
    
    # Elite Institution distribution (filtered)
    elite_institution_stats = elites_queryset.values('identifiant__institution').annotate(count=Count('identifiant__institution')).order_by('-count')
    
    # Elite Class distribution (filtered)
    elite_class_stats = elites_queryset.values('identifiant__Class').annotate(count=Count('identifiant__Class')).order_by('-count')
    
    # === ELITE NOTES STATISTICS ===
    elite_notes = NoteEtudiant.objects.filter(identifiant__id__in=elite_student_ids)
    
    # Apply same filters to notes
    if centre_filter:
        elite_notes = elite_notes.filter(identifiant__centre=centre_filter)
    if institution_filter:
        elite_notes = elite_notes.filter(identifiant__institution=institution_filter)
    if year_filter:
        elite_notes = elite_notes.filter(annee=year_filter)
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            elite_notes = elite_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            elite_notes = elite_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            elite_notes = elite_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            elite_notes = elite_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            elite_notes = elite_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            elite_notes = elite_notes.filter(identifiant__date_naissance__lte=end_date)
    
    total_elite_notes = elite_notes.count()
    elite_avg_score = elite_notes.aggregate(Avg('moyen'))['moyen__avg'] or 0
    elite_pass_rate = (elite_notes.filter(moyen__gte=10).count() / total_elite_notes * 100) if total_elite_notes > 0 else 0
    elite_excellence_rate = (elite_notes.filter(moyen__gte=16).count() / total_elite_notes * 100) if total_elite_notes > 0 else 0
    
    # Elite Grade ranges
    elite_grade_ranges = {
        '0-8': elite_notes.filter(moyen__lt=8).count(),
        '8-10': elite_notes.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': elite_notes.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': elite_notes.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': elite_notes.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': elite_notes.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': elite_notes.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # Elite Decision statistics
    elite_decision_stats = elite_notes.values('decision').annotate(count=Count('decision')).order_by('-count')
    
    # Top performing elites
    top_elite_performers = elite_notes.order_by('-moyen')[:10]
    
    # Filter options for dropdowns
    centres = Elite.objects.values_list('identifiant__centre', flat=True).distinct().exclude(identifiant__centre__isnull=True)
    institutions = Elite.objects.values_list('identifiant__institution', flat=True).distinct().exclude(identifiant__institution__isnull=True)
    years = NoteEtudiant.objects.filter(identifiant__id__in=elite_student_ids).values_list('annee', flat=True).distinct().exclude(annee__isnull=True).order_by('-annee')
    
    context = {
        "username": username,
        "profile": profileuser,
        
        # Filter parameters
        'centre_filter': centre_filter,
        'age_filter': age_filter,
        'institution_filter': institution_filter,
        'year_filter': year_filter,
        
        # Filter options
        'centres': list(centres),
        'institutions': list(institutions),
        'years': list(years),
        
        # Elite statistics
        'total_elites': total_elites,
        'archived_elites_total': archived_elites_total,
        'elite_gender_stats': elite_gender_stats,
        'elite_age_groups': elite_age_groups,
        'elite_center_stats': elite_center_stats,
        'elite_institution_stats': elite_institution_stats,
        'elite_class_stats': elite_class_stats,
        
        # Elite notes statistics
        'total_elite_notes': total_elite_notes,
        'elite_avg_score': round(elite_avg_score, 2),
        'elite_pass_rate': round(elite_pass_rate, 1),
        'elite_excellence_rate': round(elite_excellence_rate, 1),
        'elite_grade_ranges': elite_grade_ranges,
        'elite_decision_stats': elite_decision_stats,
        'top_elite_performers': top_elite_performers,
    }
    
    return render(response, "main/elite_dashboard.html", context)

@login_required(login_url='loginSingup')    
def home(response):
    """
    General dashboard view with comprehensive statistics
    """
    # User profile information
    userprofile = takeinfoUser(response)
    username = userprofile["username"]
    profileuser = userprofile["profile"]
    
    # === GENERAL STATISTICS ===
    # Exclude archived students from global totals
    total_students = Etudiant.objects.exclude(id__in=Archive.objects.values('archive_id')).count()
    total_personnel = Personnel.objects.count()
    total_notes = NoteEtudiant.objects.count()
    
    # === PERSONNEL STATISTICS ===
    personnel_gender_stats = Personnel.objects.values('genre').annotate(count=Count('genre'))
    personnel_section_stats = Personnel.objects.values('section').annotate(count=Count('section')).order_by('-count')
    personnel_situation_stats = Personnel.objects.values('situation').annotate(count=Count('situation'))
    personnel_center_stats = Personnel.objects.values('centre').annotate(count=Count('centre'))
    
    # === JAMAT STATISTICS ===
    total_jamat = Jamat.objects.count()
    jamat_gender_stats = Jamat.objects.values('genre').annotate(count=Count('genre'))
    jamat_center_stats = Jamat.objects.values('centre').annotate(count=Count('centre'))
    
    # Jamat age groups
    jamat_age_groups = {'-25': 0, '25-35': 0, '36-50': 0, '51+': 0}
    for jamat in Jamat.objects.all():
        age = jamat.age
        if age < 25:
            jamat_age_groups['-25'] += 1
        elif 25 <= age <= 35:
            jamat_age_groups['25-35'] += 1
        elif 36 <= age <= 50:
            jamat_age_groups['36-50'] += 1
        else:
            jamat_age_groups['51+'] += 1
    
    # === MADRASSAH STATISTICS ===
    total_madrassah = Madrassah.objects.count()
    madrassah_gender_stats = Madrassah.objects.values('genre').annotate(count=Count('genre'))
    madrassah_center_stats = Madrassah.objects.values('centre').annotate(count=Count('centre'))
    
    # === PENSION STATISTICS ===
    total_pensions = Pension.objects.count()
    pension_gender_stats = Pension.objects.values('genre').annotate(count=Count('genre'))
    total_pension_amount = Pension.objects.aggregate(total=Sum('pension'))['total'] or 0
    avg_pension_amount = Pension.objects.aggregate(avg=Avg('pension'))['avg'] or 0
    
    # Pension age groups
    pension_age_groups = {'-60': 0, '60-70': 0, '70+': 0}
    for pension in Pension.objects.filter(age__isnull=False):
        age = pension.age
        if age < 60:
            pension_age_groups['-60'] += 1
        elif 60 <= age <= 70:
            pension_age_groups['60-70'] += 1
        else:
            pension_age_groups['70+'] += 1
    
    # === NOTES/GRADES STATISTICS ===
    notes_decision_stats = NoteEtudiant.objects.values('decision').annotate(count=Count('decision'))
    avg_grade = NoteEtudiant.objects.aggregate(avg=Avg('moyen'))['avg'] or 0
    
    # Grade distribution
    grade_ranges = {
        '0-8': NoteEtudiant.objects.filter(moyen__lt=8).count(),
        '8-10': NoteEtudiant.objects.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': NoteEtudiant.objects.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': NoteEtudiant.objects.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': NoteEtudiant.objects.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': NoteEtudiant.objects.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': NoteEtudiant.objects.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # === ATTENDANCE STATISTICS ===
    total_attendance_records = Presence.objects.count()
    present_count = Presence.objects.filter(presence='P').count()
    absent_count = total_attendance_records - present_count
    attendance_rate = (present_count / total_attendance_records * 100) if total_attendance_records > 0 else 0
    
    # === WARNINGS STATISTICS ===
    total_warnings = Avertissement.objects.count()
    
    # Monthly attendance trend (last 6 months)
    from datetime import datetime, timedelta
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_attendance = []
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        month_present = Presence.objects.filter(
            date__range=[month_start.date(), month_end.date()],
            presence='P'
        ).count()
        month_total = Presence.objects.filter(
            date__range=[month_start.date(), month_end.date()]
        ).count()
        monthly_attendance.append({
            'month': month_start.strftime('%b %Y'),
            'rate': (month_present / month_total * 100) if month_total > 0 else 0
        })
    
    # === SORTANTS + UNIVERSITES DASHBOARD ===
    # Base querysets
    sortants_qs = Sortant.objects.select_related('sortant').all()
    universites_qs = Universite.objects.select_related('universite').all()

    total_sortants_dash = sortants_qs.count()
    total_universites_dash = universites_qs.count()
    total_combined_su = total_sortants_dash + total_universites_dash

    # Sortant breakdowns
    sortant_status_stats = sortants_qs.values('status').annotate(count=Count('status')).order_by('-count')
    sortant_placement_stats = sortants_qs.values('placement_type').annotate(count=Count('placement_type')).order_by('-count')
    sortant_poste_stats = sortants_qs.values('poste_actuel').annotate(count=Count('poste_actuel')).order_by('-count')
    sortant_entreprise_stats = sortants_qs.values('entreprise').annotate(count=Count('entreprise')).order_by('-count')
    sortant_lieu_travail_stats = sortants_qs.values('lieu_travail').annotate(count=Count('lieu_travail')).order_by('-count')
    sortant_filiere_stats = sortants_qs.values('sortant__fillier').annotate(count=Count('sortant__fillier')).order_by('-count')
    sortant_ville_stats_dash = sortants_qs.values('sortant__ville').annotate(count=Count('sortant__ville')).order_by('-count')

    # Université breakdowns (study location, filière, class, centre)
    universite_institution_stats = universites_qs.values('universite__institution').annotate(count=Count('universite__institution')).order_by('-count')
    universite_filiere_stats = universites_qs.values('universite__fillier').annotate(count=Count('universite__fillier')).order_by('-count')
    universite_class_stats = universites_qs.values('universite__Class').annotate(count=Count('universite__Class')).order_by('-count')
    universite_centre_stats = universites_qs.values('universite__centre').annotate(count=Count('universite__centre')).order_by('-count')

    context = {
        "username": username,
        "profile": profileuser,
        
        # Overall statistics
        'total_students': total_students,
        'total_personnel': total_personnel,
        'total_notes': total_notes,
        'total_jamat': total_jamat,
        'total_madrassah': total_madrassah,
        'total_pensions': total_pensions,
        'total_warnings': total_warnings,
        
        # Personnel statistics
        'personnel_gender_stats': list(personnel_gender_stats),
        'personnel_section_stats': list(personnel_section_stats),
        'personnel_situation_stats': list(personnel_situation_stats),
        'personnel_center_stats': list(personnel_center_stats),
        
        # Jamat statistics
        'jamat_gender_stats': list(jamat_gender_stats),
        'jamat_center_stats': list(jamat_center_stats),
        'jamat_age_groups': jamat_age_groups,
        
        # Madrassah statistics
        'madrassah_gender_stats': list(madrassah_gender_stats),
        'madrassah_center_stats': list(madrassah_center_stats),
        
        # Pension statistics
        'pension_gender_stats': list(pension_gender_stats),
        'total_pension_amount': total_pension_amount,
        'avg_pension_amount': round(avg_pension_amount, 2),
        'pension_age_groups': pension_age_groups,
        
        # Notes/Grades statistics
        'notes_decision_stats': list(notes_decision_stats),
        'avg_grade': round(avg_grade, 2),
        'grade_ranges': grade_ranges,
        
        # Attendance statistics
        'attendance_rate': round(attendance_rate, 1),
        'present_count': present_count,
        'absent_count': absent_count,
        'monthly_attendance': monthly_attendance,

        # Sortants + Universités (dashboard section)
        'total_sortants_dash': total_sortants_dash,
        'total_universites_dash': total_universites_dash,
        'total_combined_su': total_combined_su,
        'sortant_status_stats_dash': list(sortant_status_stats),
        'sortant_placement_stats_dash': list(sortant_placement_stats),
        'sortant_poste_stats_dash': list(sortant_poste_stats[:10]),
        'sortant_entreprise_stats_dash': list(sortant_entreprise_stats[:10]),
        'sortant_lieu_travail_stats_dash': list(sortant_lieu_travail_stats[:10]),
        'sortant_filiere_stats_dash': list(sortant_filiere_stats),
        'sortant_ville_stats_dash': list(sortant_ville_stats_dash),
        'universite_institution_stats_dash': list(universite_institution_stats),
        'universite_filiere_stats_dash': list(universite_filiere_stats),
        'universite_class_stats_dash': list(universite_class_stats),
        'universite_centre_stats_dash': list(universite_centre_stats),
    }

    return render(response, "main/home.html", context)

@login_required(login_url='loginSingup')    
def etudiants_dashboard(response):
    """
    Dedicated Etudiants dashboard view with comprehensive statistics and filtering
    """
    # User profile information
    userprofile = takeinfoUser(response)
    username = userprofile["username"]
    profileuser = userprofile["profile"]
    
    # Get filter parameters
    centre_filter = response.GET.get('centre', '')
    age_filter = response.GET.get('age', '')
    designation_filter = response.GET.get('designation', '')
    institution_filter = response.GET.get('institution', '')
    year_filter = response.GET.get('year', '')
    
    # === STUDENT STATISTICS (Main Focus) ===
    # Exclude archived students
    students_queryset = Etudiant.objects.exclude(id__in=Archive.objects.values('archive_id'))
    
    # Apply filters to students
    if centre_filter:
        center_values = get_center_filter_values(centre_filter)
        students_queryset = students_queryset.filter(centre__in=center_values)
    if designation_filter:
        students_queryset = students_queryset.filter(designation=designation_filter)
    if institution_filter:
        students_queryset = students_queryset.filter(institution=institution_filter)
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            students_queryset = students_queryset.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            students_queryset = students_queryset.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            students_queryset = students_queryset.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            students_queryset = students_queryset.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            students_queryset = students_queryset.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            students_queryset = students_queryset.filter(date_naissance__lte=end_date)
    
    total_students = students_queryset.count()
    
    # Student Gender distribution (filtered)
    student_gender_stats = students_queryset.values('genre').annotate(count=Count('genre'))
    
    # Student Age distribution (filtered)
    student_age_groups = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}
    for student in students_queryset:
        if student.date_naissance:
            today = date.today()
            age = today.year - student.date_naissance.year - ((today.month, today.day) < (student.date_naissance.month, student.date_naissance.day))
            if 3 <= age <= 10:
                student_age_groups['3-10'] += 1
            elif 11 <= age <= 14:
                student_age_groups['11-14'] += 1
            elif 15 <= age <= 18:
                student_age_groups['15-18'] += 1
            elif 19 <= age <= 21:
                student_age_groups['19-21'] += 1
            elif 22 <= age <= 25:
                student_age_groups['22-25'] += 1
            else:
                student_age_groups['26+'] += 1
    
    # Student Designation distribution (filtered)
    student_designation_stats = students_queryset.values('designation').annotate(count=Count('designation')).order_by('-count')
    
    # Student Center distribution (filtered)
    student_center_stats = students_queryset.values('centre').annotate(count=Count('centre')).order_by('-count')
    
    # Student Institution distribution (filtered)
    student_institution_stats = students_queryset.values('institution').annotate(count=Count('institution')).order_by('-count')
    
    # Student Class distribution (filtered)
    student_class_stats = students_queryset.values('Class').annotate(count=Count('Class')).order_by('-count')
    
    # === STUDENT NOTES STATISTICS ===
    student_notes = NoteEtudiant.objects.filter(identifiant__in=students_queryset)
    
    # Apply same filters to notes
    if centre_filter:
        center_values = get_center_filter_values(centre_filter)
        student_notes = student_notes.filter(identifiant__centre__in=center_values)
    if institution_filter:
        student_notes = student_notes.filter(identifiant__institution=institution_filter)
    if year_filter:
        student_notes = student_notes.filter(annee=year_filter)
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            student_notes = student_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            student_notes = student_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            student_notes = student_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            student_notes = student_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            student_notes = student_notes.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            student_notes = student_notes.filter(identifiant__date_naissance__lte=end_date)
    
    total_student_notes = student_notes.count()
    student_avg_score = student_notes.aggregate(Avg('moyen'))['moyen__avg'] or 0
    student_pass_rate = (student_notes.filter(moyen__gte=10).count() / total_student_notes * 100) if total_student_notes > 0 else 0
    student_excellence_rate = (student_notes.filter(moyen__gte=16).count() / total_student_notes * 100) if total_student_notes > 0 else 0
    
    # Student Grade ranges
    student_grade_ranges = {
        '0-8': student_notes.filter(moyen__lt=8).count(),
        '8-10': student_notes.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': student_notes.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': student_notes.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': student_notes.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': student_notes.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': student_notes.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # Student Decision statistics
    student_decision_stats = student_notes.values('decision').annotate(count=Count('decision')).order_by('-count')
    
    # Top performing students
    top_student_performers = student_notes.order_by('-moyen')[:10]
    
    # Filter options for dropdowns
    centres = students_queryset.values_list('centre', flat=True).distinct().exclude(centre__isnull=True)
    institutions = students_queryset.values_list('institution', flat=True).distinct().exclude(institution__isnull=True)
    designations = students_queryset.values_list('designation', flat=True).distinct().exclude(designation__isnull=True)
    years = student_notes.values_list('annee', flat=True).distinct().exclude(annee__isnull=True).order_by('-annee')
    
    context = {
        "username": username,
        "profile": profileuser,
        
        # Filter parameters
        'centre_filter': centre_filter,
        'age_filter': age_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'year_filter': year_filter,
        
        # Filter options
        'centres': list(centres),
        'institutions': list(institutions),
        'designations': list(designations),
        'years': list(years),
        
        # Student statistics
        'total_students': total_students,
        'student_gender_stats': student_gender_stats,
        'student_age_groups': student_age_groups,
        'student_designation_stats': student_designation_stats,
        'student_center_stats': student_center_stats,
        'student_institution_stats': student_institution_stats,
        'student_class_stats': student_class_stats,
        
        # Student notes statistics
        'total_student_notes': total_student_notes,
        'student_avg_score': round(student_avg_score, 2),
        'student_pass_rate': round(student_pass_rate, 1),
        'student_excellence_rate': round(student_excellence_rate, 1),
        'student_grade_ranges': student_grade_ranges,
        'student_decision_stats': student_decision_stats,
        'top_student_performers': top_student_performers,
    }
    
    return render(response, "main/etudiants_dashboard.html", context)

# Helper function to get the date range for filtering by age
def get_age_range(min_age, max_age):
    today = date.today()
    start_date = today.replace(year=today.year - max_age)  # Oldest date
    end_date = today.replace(year=today.year - min_age)  # Youngest date
    return start_date, end_date

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def student(request):
    # Exclude archived students from list and stats
    students = Etudiant.objects.exclude(id__in=Archive.objects.values('archive_id'))
    
    # Store original queryset for statistics
    # For statistics, use non-archived base queryset
    original_students = Etudiant.objects.exclude(id__in=Archive.objects.values('archive_id'))
    total_students = original_students.count()

    # Get the filters
    search_query = request.GET.get('search', '')
    center_filter = request.GET.get('centre', '')
    fillier_filter = request.GET.get('fillier', '')
    class_filter = request.GET.get('class', '')
    genre_filter = request.GET.get('genre', '')
    institution_filter = request.GET.get('institution', '')
    age_filter = request.GET.get('age', '')
    designation_filter = request.GET.get('designation', '')
    status_filter = request.GET.get('status', '')

    # Apply filters
    if search_query:
        from django.db.models import Q
        students = students.filter(
            Q(nom__icontains=search_query) |
            Q(identifiant__icontains=search_query) |
            Q(telephone__icontains=search_query) |
            Q(institution__icontains=search_query) |
            Q(ville__icontains=search_query) |
            Q(fillier__icontains=search_query) |
            Q(nom_pere__icontains=search_query) |
            Q(nom_mere__icontains=search_query)
        )
    if center_filter:
        center_values = get_center_filter_values(center_filter)
        students = students.filter(centre__in=center_values)
    if fillier_filter:
        students = students.filter(fillier=fillier_filter)
    if class_filter:
        students = students.filter(Class=class_filter)
    if genre_filter:
        students = students.filter(genre=genre_filter)
    if institution_filter:
        students = students.filter(institution=institution_filter)
    if designation_filter:
        students = students.filter(designation=designation_filter)
    if status_filter:
        students = students.filter(status=status_filter)

    # Apply age filter based on the categories
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            students = students.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            students = students.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            students = students.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            students = students.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            students = students.filter(date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            students = students.filter(date_naissance__lte=end_date)

    # Calculate statistics
    filtered_count = students.count()
    
    # Gender statistics
    male_count = original_students.filter(genre='M').count()
    female_count = original_students.filter(genre='F').count()
    male_percentage = round((male_count / total_students * 100), 1) if total_students > 0 else 0
    female_percentage = round((female_count / total_students * 100), 1) if total_students > 0 else 0
    
    # Designation statistics
    designation_stats = original_students.values('designation').annotate(count=Count('designation')).order_by('-count')
    
    # Center statistics
    center_stats = original_students.values('centre').annotate(count=Count('centre')).order_by('-count')
    
    # Institution statistics
    institution_stats = original_students.values('institution').annotate(count=Count('institution')).order_by('-count')
    
    # Age group statistics
    age_groups = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}
    for student in original_students:
        today = date.today()
        age = today.year - student.date_naissance.year - ((today.month, today.day) < (student.date_naissance.month, student.date_naissance.day))
        if 3 <= age <= 10:
            age_groups['3-10'] += 1
        elif 11 <= age <= 14:
            age_groups['11-14'] += 1
        elif 15 <= age <= 18:
            age_groups['15-18'] += 1
        elif 19 <= age <= 21:
            age_groups['19-21'] += 1
        elif 22 <= age <= 25:
            age_groups['22-25'] += 1
        else:
            age_groups['26+'] += 1

    # Pagination
    paginator = Paginator(students, 30)  # Show 30 students per page
    page_number = request.GET.get('page', 1)  # Default to page 1
    students = paginator.get_page(page_number)

    # Get distinct values for filter options
    centers = Etudiant.objects.values_list('centre', flat=True).distinct()
    filliers = Etudiant.objects.values_list('fillier', flat=True).distinct()
    classes = Etudiant.objects.values_list('Class', flat=True).distinct()
    genres = Etudiant.objects.values_list('genre', flat=True).distinct()
    institutions = Etudiant.objects.values_list('institution', flat=True).distinct()
    designations = Etudiant.objects.values_list('designation', flat=True).distinct()
    statuses = Etudiant.objects.values_list('status', flat=True).distinct()

    datahead = ['ID', "Date de naissance", "Age", 'Nom du Parent (Père)', 'Nom du Parent (Mère)', 'Téléphone', 'Téléphone (Père/Mère)', "Designation", "Institution", 'Ville', 'Filière', 'Classe', 'Centre', "Date d'Entrée", "Date de Sortie"]

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # Check if the request is AJAX
        student_data = []
        for student in students:
            student_data.append({
                'id': student.id,
                'nom': student.nom,
                'image': student.imageprofile.url if student.imageprofile else '',
                'email': student.email or ' ',
                'identifiant': student.identifiant,
                'Class': student.Class,
                'telephone': student.telephone or ' ',
                'centre': student.centre,
            })
        return JsonResponse({
            'students': student_data,
            'has_next': students.has_next(),
            'has_previous': students.has_previous(),
            'page': page_number,
            'num_pages': paginator.num_pages,
        })

    context = {
        'students': students,
        'search_query': search_query,
        'centre_filter': center_filter,
        'fillier_filter': fillier_filter,
        'class_filter': class_filter,
        'age_filter':age_filter,
        'genre_filter': genre_filter,
        'institution_filter': institution_filter,
        "designation_filter":designation_filter,
        'centers': centers,
        'filliers': filliers,
        'classes': classes,
        'genres': genres,
        'institutions': institutions,
        'designations': designations,
        'statuses': statuses,
        'status_filter': status_filter,
        'datahead': datahead,
        # Statistics
        'total_students': total_students,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'designation_stats': designation_stats,
        'center_stats': center_stats,
        'institution_stats': institution_stats,
        'age_groups': age_groups,
    }
    return render(request, 'main/student.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def archived_students(request):
    archived_qs = Archive.objects.select_related('archive').all()

    # Filters
    search_query = request.GET.get('search', '')
    center_filter = request.GET.get('centre', '')
    fillier_filter = request.GET.get('fillier', '')
    class_filter = request.GET.get('class', '')
    genre_filter = request.GET.get('genre', '')
    institution_filter = request.GET.get('institution', '')
    age_filter = request.GET.get('age', '')
    designation_filter = request.GET.get('designation', '')
    archive_type_filter = request.GET.get('archive_type', '')
    raison_filter = request.GET.get('raison', '')

    if search_query:
        from django.db.models import Q
        archived_qs = archived_qs.filter(
            Q(archive__nom__icontains=search_query) |
            Q(archive__identifiant__icontains=search_query) |
            Q(archive__telephone__icontains=search_query) |
            Q(archive__institution__icontains=search_query) |
            Q(archive__ville__icontains=search_query) |
            Q(archive__fillier__icontains=search_query)
        )
    if center_filter:
        center_values = get_center_filter_values(center_filter)
        archived_qs = archived_qs.filter(archive__centre__in=center_values)
    if fillier_filter:
        archived_qs = archived_qs.filter(archive__fillier=fillier_filter)
    if class_filter:
        archived_qs = archived_qs.filter(archive__Class=class_filter)
    if genre_filter:
        archived_qs = archived_qs.filter(archive__genre=genre_filter)
    if institution_filter:
        archived_qs = archived_qs.filter(archive__institution=institution_filter)
    if designation_filter:
        archived_qs = archived_qs.filter(archive__designation=designation_filter)
    if archive_type_filter:
        archived_qs = archived_qs.filter(archive_type=archive_type_filter)
    if raison_filter:
        archived_qs = archived_qs.filter(raison=raison_filter)

    # Age ranges based on student birthdate
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            archived_qs = archived_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            archived_qs = archived_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            archived_qs = archived_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            archived_qs = archived_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            archived_qs = archived_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            from datetime import date as _date
            end_date = _date.today().replace(year=_date.today().year - 26)
            archived_qs = archived_qs.filter(archive__date_naissance__lte=end_date)

    # === Archived Statistics ===
    total_archived = archived_qs.count()
    archived_gender_stats = archived_qs.values('archive__genre').annotate(count=Count('archive__genre'))
    archived_center_stats = archived_qs.values('archive__centre').annotate(count=Count('archive__centre')).order_by('-count')
    archived_designation_stats = archived_qs.values('archive__designation').annotate(count=Count('archive__designation')).order_by('-count')
    archived_institution_stats = archived_qs.values('archive__institution').annotate(count=Count('archive__institution')).order_by('-count')
    archived_class_stats = archived_qs.values('archive__Class').annotate(count=Count('archive__Class')).order_by('-count')
    archived_type_stats = archived_qs.values('archive_type').annotate(count=Count('archive_type')).order_by('-count')
    archived_raison_stats = archived_qs.values('raison').annotate(count=Count('raison')).order_by('-count')

    # Age buckets
    archived_age_groups = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}
    from datetime import date as _date
    for a in archived_qs:
        if a.archive and a.archive.date_naissance:
            today = _date.today()
            age = today.year - a.archive.date_naissance.year - ((today.month, today.day) < (a.archive.date_naissance.month, a.archive.date_naissance.day))
            if 3 <= age <= 10:
                archived_age_groups['3-10'] += 1
            elif 11 <= age <= 14:
                archived_age_groups['11-14'] += 1
            elif 15 <= age <= 18:
                archived_age_groups['15-18'] += 1
            elif 19 <= age <= 21:
                archived_age_groups['19-21'] += 1
            elif 22 <= age <= 25:
                archived_age_groups['22-25'] += 1
            else:
                archived_age_groups['26+'] += 1

    # Options for filters
    centers = list(Archive.objects.values_list('archive__centre', flat=True).distinct().exclude(archive__centre__isnull=True))
    filliers = list(Archive.objects.values_list('archive__fillier', flat=True).distinct().exclude(archive__fillier__isnull=True))
    classes = list(Archive.objects.values_list('archive__Class', flat=True).distinct().exclude(archive__Class__isnull=True))
    genres = list(Archive.objects.values_list('archive__genre', flat=True).distinct().exclude(archive__genre__isnull=True))
    institutions = list(Archive.objects.values_list('archive__institution', flat=True).distinct().exclude(archive__institution__isnull=True))
    designations = list(Archive.objects.values_list('archive__designation', flat=True).distinct().exclude(archive__designation__isnull=True))
    archive_types = list(Archive.objects.values_list('archive_type', flat=True).distinct().exclude(archive_type__isnull=True))
    raisons = list(Archive.objects.values_list('raison', flat=True).distinct().exclude(raison__isnull=True))

    context = {
        'archived': archived_qs,
        'total_archived': total_archived,
        'archived_gender_stats': list(archived_gender_stats),
        'archived_center_stats': list(archived_center_stats),
        'archived_designation_stats': list(archived_designation_stats),
        'archived_institution_stats': list(archived_institution_stats),
        'archived_class_stats': list(archived_class_stats),
        'archived_type_stats': list(archived_type_stats),
        'archived_raison_stats': list(archived_raison_stats),
        'archived_age_groups': archived_age_groups,
        'search_query': search_query,
        'centre_filter': center_filter,
        'fillier_filter': fillier_filter,
        'class_filter': class_filter,
        'age_filter': age_filter,
        'genre_filter': genre_filter,
        'institution_filter': institution_filter,
        'designation_filter': designation_filter,
        'archive_type_filter': archive_type_filter,
        'raison_filter': raison_filter,
        'centers': centers,
        'filliers': filliers,
        'classes': classes,
        'genres': genres,
        'institutions': institutions,
        'designations': designations,
        'archive_types': archive_types,
        'raisons': raisons,
    }

    return render(request, 'main/archived_students.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def archived_orphelins(request):
    """
    View for displaying archived orphelins (students with archive_type = 'Orphelin')
    """
    # Get archived orphelins - students that are archived with archive_type = 'Orphelin'
    archived_orphelins_qs = Archive.objects.filter(archive_type='Orphelin').select_related('archive')

    # Filters
    search_query = request.GET.get('search', '')
    center_filter = request.GET.get('centre', '')
    fillier_filter = request.GET.get('fillier', '')
    class_filter = request.GET.get('class', '')
    genre_filter = request.GET.get('genre', '')
    institution_filter = request.GET.get('institution', '')
    age_filter = request.GET.get('age', '')
    designation_filter = request.GET.get('designation', '')
    archive_type_filter = request.GET.get('archive_type', '')
    raison_filter = request.GET.get('raison', '')
    orphan_status_filter = request.GET.get('orphan_status', '')

    if search_query:
        from django.db.models import Q
        archived_orphelins_qs = archived_orphelins_qs.filter(
            Q(archive__nom__icontains=search_query) |
            Q(archive__identifiant__icontains=search_query) |
            Q(archive__telephone__icontains=search_query) |
            Q(archive__institution__icontains=search_query) |
            Q(archive__ville__icontains=search_query) |
            Q(archive__fillier__icontains=search_query)
        )
    if center_filter:
        center_values = get_center_filter_values(center_filter)
        archived_orphelins_qs = archived_orphelins_qs.filter(archive__centre__in=center_values)
    if fillier_filter:
        archived_orphelins_qs = archived_orphelins_qs.filter(archive__fillier=fillier_filter)
    if class_filter:
        archived_orphelins_qs = archived_orphelins_qs.filter(archive__Class=class_filter)
    if genre_filter:
        archived_orphelins_qs = archived_orphelins_qs.filter(archive__genre=genre_filter)
    if institution_filter:
        archived_orphelins_qs = archived_orphelins_qs.filter(archive__institution=institution_filter)
    if designation_filter:
        archived_orphelins_qs = archived_orphelins_qs.filter(archive__designation=designation_filter)
    if archive_type_filter:
        archived_orphelins_qs = archived_orphelins_qs.filter(archive_type=archive_type_filter)
    if raison_filter:
        archived_orphelins_qs = archived_orphelins_qs.filter(raison=raison_filter)

    # Age ranges based on student birthdate
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            archived_orphelins_qs = archived_orphelins_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            archived_orphelins_qs = archived_orphelins_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            archived_orphelins_qs = archived_orphelins_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            archived_orphelins_qs = archived_orphelins_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            archived_orphelins_qs = archived_orphelins_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            from datetime import date as _date
            end_date = _date.today().replace(year=_date.today().year - 26)
            archived_orphelins_qs = archived_orphelins_qs.filter(archive__date_naissance__lte=end_date)

    # === Archived Orphelins Statistics ===
    total_archived_orphelins = archived_orphelins_qs.count()
    archived_orphelins_gender_stats = archived_orphelins_qs.values('archive__genre').annotate(count=Count('archive__genre'))
    archived_orphelins_center_stats = archived_orphelins_qs.values('archive__centre').annotate(count=Count('archive__centre')).order_by('-count')
    archived_orphelins_designation_stats = archived_orphelins_qs.values('archive__designation').annotate(count=Count('archive__designation')).order_by('-count')
    archived_orphelins_institution_stats = archived_orphelins_qs.values('archive__institution').annotate(count=Count('archive__institution')).order_by('-count')
    archived_orphelins_class_stats = archived_orphelins_qs.values('archive__Class').annotate(count=Count('archive__Class')).order_by('-count')
    archived_orphelins_raison_stats = archived_orphelins_qs.values('raison').annotate(count=Count('raison')).order_by('-count')

    # Age buckets
    archived_orphelins_age_groups = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}
    from datetime import date as _date
    for a in archived_orphelins_qs:
        if a.archive and a.archive.date_naissance:
            today = _date.today()
            age = today.year - a.archive.date_naissance.year - ((today.month, today.day) < (a.archive.date_naissance.month, a.archive.date_naissance.day))
            if 3 <= age <= 10:
                archived_orphelins_age_groups['3-10'] += 1
            elif 11 <= age <= 14:
                archived_orphelins_age_groups['11-14'] += 1
            elif 15 <= age <= 18:
                archived_orphelins_age_groups['15-18'] += 1
            elif 19 <= age <= 21:
                archived_orphelins_age_groups['19-21'] += 1
            elif 22 <= age <= 25:
                archived_orphelins_age_groups['22-25'] += 1
            else:
                archived_orphelins_age_groups['26+'] += 1

    # Get orphan status for archived orphelins
    orphan_status_list = []
    for archived_orphelin in archived_orphelins_qs:
        try:
            orphelin_record = Orphelin.objects.get(identifiant=archived_orphelin.archive)
            orphan_status_list.append(orphelin_record.décedé)
        except Orphelin.DoesNotExist:
            orphan_status_list.append('Non orphelin')

    # Count orphan status
    from collections import Counter
    orphan_status_counts = Counter(orphan_status_list)
    archived_orphelins_orphan_status_stats = [{'décedé': status, 'count': count} for status, count in orphan_status_counts.items()]

    # Options for filters
    centers = list(archived_orphelins_qs.values_list('archive__centre', flat=True).distinct().exclude(archive__centre__isnull=True))
    filliers = list(archived_orphelins_qs.values_list('archive__fillier', flat=True).distinct().exclude(archive__fillier__isnull=True))
    classes = list(archived_orphelins_qs.values_list('archive__Class', flat=True).distinct().exclude(archive__Class__isnull=True))
    genres = list(archived_orphelins_qs.values_list('archive__genre', flat=True).distinct().exclude(archive__genre__isnull=True))
    institutions = list(archived_orphelins_qs.values_list('archive__institution', flat=True).distinct().exclude(archive__institution__isnull=True))
    designations = list(archived_orphelins_qs.values_list('archive__designation', flat=True).distinct().exclude(archive__designation__isnull=True))
    raisons = list(archived_orphelins_qs.values_list('raison', flat=True).distinct().exclude(raison__isnull=True))
    orphan_statuses = list(set(orphan_status_list))
    
    # Get archive choices
    archive_choices = [choice[0] for choice in Archive.archive_choice]

    context = {
        'archived_orphelins': archived_orphelins_qs,
        'total_archived_orphelins': total_archived_orphelins,
        'archived_orphelins_gender_stats': list(archived_orphelins_gender_stats),
        'archived_orphelins_center_stats': list(archived_orphelins_center_stats),
        'archived_orphelins_designation_stats': list(archived_orphelins_designation_stats),
        'archived_orphelins_institution_stats': list(archived_orphelins_institution_stats),
        'archived_orphelins_class_stats': list(archived_orphelins_class_stats),
        'archived_orphelins_raison_stats': list(archived_orphelins_raison_stats),
        'archived_orphelins_orphan_status_stats': archived_orphelins_orphan_status_stats,
        'archived_orphelins_age_groups': archived_orphelins_age_groups,
        'search_query': search_query,
        'centre_filter': center_filter,
        'fillier_filter': fillier_filter,
        'class_filter': class_filter,
        'age_filter': age_filter,
        'genre_filter': genre_filter,
        'institution_filter': institution_filter,
        'designation_filter': designation_filter,
        'archive_type_filter': archive_type_filter,
        'raison_filter': raison_filter,
        'orphan_status_filter': orphan_status_filter,
        'centers': centers,
        'filliers': filliers,
        'classes': classes,
        'genres': genres,
        'institutions': institutions,
        'designations': designations,
        'raisons': raisons,
        'archive_choices': archive_choices,
        'orphan_statuses': orphan_statuses,
    }

    return render(request, 'main/archived_orphelins.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def archived_jamats(request):
    """
    View for displaying archived jamats
    """
    archived_jamats_qs = ArchiveJamat.objects.select_related('jamat')

    search_query = request.GET.get('search', '')
    center_filter = request.GET.get('centre', '')
    genre_filter = request.GET.get('genre', '')
    age_filter = request.GET.get('age', '')
    travail_filter = request.GET.get('travail', '')
    adress_filter = request.GET.get('adress', '')
    conversion_year_filter = request.GET.get('conversion_year', '')
    archive_type_filter = request.GET.get('archive_type', '')
    raison_filter = request.GET.get('raison', '')

    if search_query:
        archived_jamats_qs = archived_jamats_qs.filter(
            Q(jamat__nom__icontains=search_query) |
            Q(jamat__jamatid__icontains=search_query) |
            Q(jamat__telephone__icontains=search_query) |
            Q(jamat__adress__icontains=search_query) |
            Q(jamat__travail__icontains=search_query)
        )
    if center_filter:
        archived_jamats_qs = archived_jamats_qs.filter(jamat__centre=center_filter)
    if genre_filter:
        archived_jamats_qs = archived_jamats_qs.filter(jamat__genre=genre_filter)
    if travail_filter:
        archived_jamats_qs = archived_jamats_qs.filter(jamat__travail=travail_filter)
    if adress_filter:
        archived_jamats_qs = archived_jamats_qs.filter(jamat__adress=adress_filter)
    if conversion_year_filter:
        archived_jamats_qs = archived_jamats_qs.filter(jamat__conversion_year=conversion_year_filter)
    if archive_type_filter:
        archived_jamats_qs = archived_jamats_qs.filter(archive_type=archive_type_filter)
    if raison_filter:
        archived_jamats_qs = archived_jamats_qs.filter(raison=raison_filter)
    if age_filter:
        if age_filter == '-25':
            archived_jamats_qs = archived_jamats_qs.filter(jamat__age__lt=25)
        elif age_filter == '25-35':
            archived_jamats_qs = archived_jamats_qs.filter(jamat__age__gte=25, jamat__age__lte=35)
        elif age_filter == '36-50':
            archived_jamats_qs = archived_jamats_qs.filter(jamat__age__gte=36, jamat__age__lte=50)
        elif age_filter == '51+':
            archived_jamats_qs = archived_jamats_qs.filter(jamat__age__gt=50)

    total_archived_jamats = archived_jamats_qs.count()
    archived_jamats_gender_stats = archived_jamats_qs.values('jamat__genre').annotate(count=Count('jamat__genre'))
    archived_jamats_center_stats = archived_jamats_qs.values('jamat__centre').annotate(count=Count('jamat__centre')).order_by('-count')
    archived_jamats_work_stats = archived_jamats_qs.values('jamat__travail').annotate(count=Count('jamat__travail')).order_by('-count')
    archived_jamats_location_stats = archived_jamats_qs.values('jamat__adress').annotate(count=Count('jamat__adress')).order_by('-count')
    archived_jamats_conversion_stats = archived_jamats_qs.values('jamat__conversion_year').annotate(count=Count('jamat__conversion_year')).order_by('-count')

    archived_jamats_age_groups = {'-25': 0, '25-35': 0, '36-50': 0, '51+': 0}
    for a in archived_jamats_qs:
        if a.jamat and a.jamat.age is not None:
            age = a.jamat.age
            if age < 25:
                archived_jamats_age_groups['-25'] += 1
            elif 25 <= age <= 35:
                archived_jamats_age_groups['25-35'] += 1
            elif 36 <= age <= 50:
                archived_jamats_age_groups['36-50'] += 1
            else:
                archived_jamats_age_groups['51+'] += 1

    centers = list(archived_jamats_qs.values_list('jamat__centre', flat=True).distinct().exclude(jamat__centre__isnull=True))
    genres = list(archived_jamats_qs.values_list('jamat__genre', flat=True).distinct().exclude(jamat__genre__isnull=True))
    travails = list(archived_jamats_qs.values_list('jamat__travail', flat=True).distinct().exclude(jamat__travail__isnull=True))
    adresses = list(archived_jamats_qs.values_list('jamat__adress', flat=True).distinct().exclude(jamat__adress__isnull=True))
    conversion_years = list(archived_jamats_qs.values_list('jamat__conversion_year', flat=True).distinct().exclude(jamat__conversion_year__isnull=True))
    raisons = list(archived_jamats_qs.values_list('raison', flat=True).distinct().exclude(raison__isnull=True))
    archive_choices = [choice[0] for choice in ArchiveJamat.archive_choice]

    context = {
        'archived_jamats': archived_jamats_qs,
        'total_archived_jamats': total_archived_jamats,
        'archived_jamats_gender_stats': list(archived_jamats_gender_stats),
        'archived_jamats_center_stats': list(archived_jamats_center_stats),
        'archived_jamats_work_stats': list(archived_jamats_work_stats),
        'archived_jamats_location_stats': list(archived_jamats_location_stats),
        'archived_jamats_conversion_stats': list(archived_jamats_conversion_stats),
        'archived_jamats_age_groups': archived_jamats_age_groups,
        'search_query': search_query,
        'centre_filter': center_filter,
        'genre_filter': genre_filter,
        'age_filter': age_filter,
        'travail_filter': travail_filter,
        'adress_filter': adress_filter,
        'conversion_year_filter': conversion_year_filter,
        'archive_type_filter': archive_type_filter,
        'raison_filter': raison_filter,
        'centers': centers,
        'genres': genres,
        'travails': travails,
        'adresses': adresses,
        'conversion_years': conversion_years,
        'raisons': raisons,
        'archive_choices': archive_choices,
    }

    return render(request, 'main/archived_jamats.html', context)


@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def archived_madrassahs(request):
    """Archives des profils madrassah (ArchiveMadrassah)."""
    archived_qs = ArchiveMadrassah.objects.select_related('madrassah')

    search_query = request.GET.get('search', '')
    centre_filter = request.GET.get('centre', '')
    genre_filter = request.GET.get('genre', '')
    archive_type_filter = request.GET.get('archive_type', '')
    raison_filter = request.GET.get('raison', '')

    if search_query:
        archived_qs = archived_qs.filter(
            Q(madrassah__nom__icontains=search_query)
            | Q(madrassah__madrassahid__icontains=search_query)
            | Q(madrassah__parent__icontains=search_query)
            | Q(madrassah__adress__icontains=search_query)
        )
    if centre_filter:
        archived_qs = archived_qs.filter(madrassah__centre=centre_filter)
    if genre_filter:
        archived_qs = archived_qs.filter(madrassah__genre=genre_filter)
    if archive_type_filter:
        archived_qs = archived_qs.filter(archive_type=archive_type_filter)
    if raison_filter:
        archived_qs = archived_qs.filter(raison=raison_filter)

    total_archived = archived_qs.count()
    archived_gender_stats = archived_qs.values('madrassah__genre').annotate(count=Count('madrassah__genre'))
    archived_center_stats = (
        archived_qs.values('madrassah__centre').annotate(count=Count('madrassah__centre')).order_by('-count')
    )

    centers = list(
        archived_qs.values_list('madrassah__centre', flat=True).distinct().exclude(madrassah__centre__isnull=True)
    )
    genres = list(
        archived_qs.values_list('madrassah__genre', flat=True).distinct().exclude(madrassah__genre__isnull=True)
    )
    raisons = list(archived_qs.values_list('raison', flat=True).distinct().exclude(raison__isnull=True))
    archive_choices = [choice[0] for choice in ArchiveMadrassah.archive_choice]

    context = {
        'archived_madrassahs': archived_qs,
        'total_archived_madrassahs': total_archived,
        'archived_madrassah_gender_stats': list(archived_gender_stats),
        'archived_madrassah_center_stats': list(archived_center_stats),
        'search_query': search_query,
        'centre_filter': centre_filter,
        'genre_filter': genre_filter,
        'archive_type_filter': archive_type_filter,
        'raison_filter': raison_filter,
        'centers': centers,
        'genres': genres,
        'raisons': raisons,
        'archive_choices': archive_choices,
    }
    return render(request, 'main/archived_madrassahs.html', context)


@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def archived_elites(request):
    """
    View for displaying archived elites (students with archive_type = 'Elite')
    """
    # Get archived elites - students that are archived with archive_type = 'Elite'
    archived_elites_qs = Archive.objects.filter(archive_type='Elite').select_related('archive')

    # Filters
    search_query = request.GET.get('search', '')
    center_filter = request.GET.get('centre', '')
    fillier_filter = request.GET.get('fillier', '')
    class_filter = request.GET.get('class', '')
    genre_filter = request.GET.get('genre', '')
    institution_filter = request.GET.get('institution', '')
    age_filter = request.GET.get('age', '')
    designation_filter = request.GET.get('designation', '')
    archive_type_filter = request.GET.get('archive_type', '')
    raison_filter = request.GET.get('raison', '')

    if search_query:
        archived_elites_qs = archived_elites_qs.filter(
            Q(archive__nom__icontains=search_query) |
            Q(archive__identifiant__icontains=search_query) |
            Q(archive__telephone__icontains=search_query) |
            Q(archive__institution__icontains=search_query) |
            Q(archive__ville__icontains=search_query) |
            Q(archive__fillier__icontains=search_query)
        )
    if center_filter:
        archived_elites_qs = archived_elites_qs.filter(archive__centre=center_filter)
    if fillier_filter:
        archived_elites_qs = archived_elites_qs.filter(archive__fillier=fillier_filter)
    if class_filter:
        archived_elites_qs = archived_elites_qs.filter(archive__Class=class_filter)
    if genre_filter:
        archived_elites_qs = archived_elites_qs.filter(archive__genre=genre_filter)
    if institution_filter:
        archived_elites_qs = archived_elites_qs.filter(archive__institution=institution_filter)
    if designation_filter:
        archived_elites_qs = archived_elites_qs.filter(archive__designation=designation_filter)
    if archive_type_filter:
        archived_elites_qs = archived_elites_qs.filter(archive_type=archive_type_filter)
    if raison_filter:
        archived_elites_qs = archived_elites_qs.filter(raison=raison_filter)
    if age_filter:
        today = date.today()
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            archived_elites_qs = archived_elites_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            archived_elites_qs = archived_elites_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            archived_elites_qs = archived_elites_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            archived_elites_qs = archived_elites_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            archived_elites_qs = archived_elites_qs.filter(archive__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            archived_elites_qs = archived_elites_qs.filter(archive__date_naissance__lte=end_date)

    # === Archived Elites Statistics ===
    total_archived_elites = archived_elites_qs.count()
    archived_elites_gender_stats = archived_elites_qs.values('archive__genre').annotate(count=Count('archive__genre'))
    archived_elites_center_stats = archived_elites_qs.values('archive__centre').annotate(count=Count('archive__centre')).order_by('-count')
    archived_elites_designation_stats = archived_elites_qs.values('archive__designation').annotate(count=Count('archive__designation')).order_by('-count')
    archived_elites_institution_stats = archived_elites_qs.values('archive__institution').annotate(count=Count('archive__institution')).order_by('-count')
    archived_elites_class_stats = archived_elites_qs.values('archive__Class').annotate(count=Count('archive__Class')).order_by('-count')
    archived_elites_raison_stats = archived_elites_qs.values('raison').annotate(count=Count('raison')).order_by('-count')

    # Age distribution for archived elites
    archived_elites_age_groups = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}
    for a in archived_elites_qs:
        if a.archive and a.archive.date_naissance:
            today = date.today()
            age = today.year - a.archive.date_naissance.year - ((today.month, today.day) < (a.archive.date_naissance.month, a.archive.date_naissance.day))
            if 3 <= age <= 10:
                archived_elites_age_groups['3-10'] += 1
            elif 11 <= age <= 14:
                archived_elites_age_groups['11-14'] += 1
            elif 15 <= age <= 18:
                archived_elites_age_groups['15-18'] += 1
            elif 19 <= age <= 21:
                archived_elites_age_groups['19-21'] += 1
            elif 22 <= age <= 25:
                archived_elites_age_groups['22-25'] += 1
            else:
                archived_elites_age_groups['26+'] += 1

    # Filter options
    centers = list(Archive.objects.filter(archive_type='Elite').values_list('archive__centre', flat=True).distinct().exclude(archive__centre__isnull=True))
    filliers = list(Archive.objects.filter(archive_type='Elite').values_list('archive__fillier', flat=True).distinct().exclude(archive__fillier__isnull=True))
    classes = list(Archive.objects.filter(archive_type='Elite').values_list('archive__Class', flat=True).distinct().exclude(archive__Class__isnull=True))
    genres = list(Archive.objects.filter(archive_type='Elite').values_list('archive__genre', flat=True).distinct().exclude(archive__genre__isnull=True))
    institutions = list(Archive.objects.filter(archive_type='Elite').values_list('archive__institution', flat=True).distinct().exclude(archive__institution__isnull=True))
    designations = list(Archive.objects.filter(archive_type='Elite').values_list('archive__designation', flat=True).distinct().exclude(archive__designation__isnull=True))
    archive_types = list(Archive.objects.values_list('archive_type', flat=True).distinct().exclude(archive_type__isnull=True))
    raisons = list(Archive.objects.filter(archive_type='Elite').values_list('raison', flat=True).distinct().exclude(raison__isnull=True))

    # Archive choices for the form
    archive_choices = [
        ('Elite', 'Elite'),
    ]

    context = {
        'archived_elites': archived_elites_qs,
        'total_archived_elites': total_archived_elites,
        'archived_elites_gender_stats': list(archived_elites_gender_stats),
        'archived_elites_center_stats': list(archived_elites_center_stats),
        'archived_elites_designation_stats': list(archived_elites_designation_stats),
        'archived_elites_institution_stats': list(archived_elites_institution_stats),
        'archived_elites_class_stats': list(archived_elites_class_stats),
        'archived_elites_raison_stats': list(archived_elites_raison_stats),
        'archived_elites_age_groups': archived_elites_age_groups,
        'search_query': search_query,
        'center_filter': center_filter,
        'fillier_filter': fillier_filter,
        'class_filter': class_filter,
        'genre_filter': genre_filter,
        'institution_filter': institution_filter,
        'age_filter': age_filter,
        'designation_filter': designation_filter,
        'archive_type_filter': archive_type_filter,
        'raison_filter': raison_filter,
        'centers': centers,
        'filliers': filliers,
        'classes': classes,
        'genres': genres,
        'institutions': institutions,
        'designations': designations,
        'archive_types': archive_types,
        'raisons': raisons,
        'archive_choices': archive_choices,
    }

    return render(request, 'main/archived_elites.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def universite(request):
    universites = Universite.objects.all()
    
    # Store original queryset for statistics
    original_universites = Universite.objects.all()
    total_universites = original_universites.count()

    # Get the filters
    search_query = request.GET.get('search', '')
    center_filter = request.GET.get('centre', '')
    fillier_filter = request.GET.get('fillier', '')
    class_filter = request.GET.get('class', '')
    genre_filter = request.GET.get('genre', '')
    institution_filter = request.GET.get('institution', '')
    age_filter = request.GET.get('age', '')
    designation_filter = request.GET.get('designation', '')

    # Apply filters
    if search_query:
        universites = universites.filter(universite__nom__icontains=search_query)
    if center_filter:
        universites = universites.filter(universite__centre=center_filter)
    if fillier_filter:
        universites = universites.filter(universite__fillier=fillier_filter)
    if class_filter:
        universites = universites.filter(universite__Class=class_filter)
    if genre_filter:
        universites = universites.filter(universite__genre=genre_filter)
    if institution_filter:
        universites = universites.filter(universite__institution=institution_filter)
    if designation_filter:
        universites = universites.filter(universite__designation=designation_filter)

    # Apply age filter based on the categories
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            universites = universites.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            universites = universites.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18)
            universites = universites.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            universites = universites.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            universites = universites.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            universites = universites.filter(universite__date_naissance__lte=end_date)

    # Calculate statistics
    filtered_count = universites.count()
    
    # Gender statistics
    male_count = original_universites.filter(universite__genre='M').count()
    female_count = original_universites.filter(universite__genre='F').count()
    male_percentage = round((male_count / total_universites * 100), 1) if total_universites > 0 else 0
    female_percentage = round((female_count / total_universites * 100), 1) if total_universites > 0 else 0

    # Pagination
    paginator = Paginator(universites, 15)  # Show 15 universities per page
    page_number = request.GET.get('page')
    universites = paginator.get_page(page_number)

    # Get unique values for filters
    centers = Etudiant.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True)
    filliers = Etudiant.objects.values_list('fillier', flat=True).distinct().exclude(fillier__isnull=True)
    classes = Etudiant.objects.values_list('Class', flat=True).distinct().exclude(Class__isnull=True)
    genres = Etudiant.objects.values_list('genre', flat=True).distinct().exclude(genre__isnull=True)
    institutions = Etudiant.objects.values_list('institution', flat=True).distinct().exclude(institution__isnull=True)
    designations = Etudiant.objects.values_list('designation', flat=True).distinct().exclude(designation__isnull=True)

    # Statistics for charts/cards
    designation_stats = original_universites.values('universite__designation').annotate(count=Count('universite__designation')).order_by('-count')
    center_stats = original_universites.values('universite__centre').annotate(count=Count('universite__centre')).order_by('-count')
    institution_stats = original_universites.values('universite__institution').annotate(count=Count('universite__institution')).order_by('-count')
    
    # Age groups calculation
    age_groups = {'18-21': 0, '22-25': 0, '26-30': 0, '31+': 0}
    for univ in original_universites:
        if univ.universite and univ.universite.date_naissance:
            age = univ.universite.Age()
            if 18 <= age <= 21:
                age_groups['18-21'] += 1
            elif 22 <= age <= 25:
                age_groups['22-25'] += 1
            elif 26 <= age <= 30:
                age_groups['26-30'] += 1
            else:
                age_groups['31+'] += 1

    context = {
        'universites': universites,
        'search_query': search_query,
        'centre_filter': center_filter,
        'fillier_filter': fillier_filter,
        'class_filter': class_filter,
        'age_filter': age_filter,
        'genre_filter': genre_filter,
        'institution_filter': institution_filter,
        'designation_filter': designation_filter,
        'centers': centers,
        'filliers': filliers,
        'classes': classes,
        'genres': genres,
        'institutions': institutions,
        'designations': designations,
        # Statistics
        'total_universites': total_universites,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'designation_stats': designation_stats,
        'center_stats': center_stats,
        'institution_stats': institution_stats,
        'age_groups': age_groups,
    }
    return render(request, 'main/universite.html', context)

@login_required(login_url='loginSingup')    
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def universite_dashboard(response):
    """
    Dedicated Université dashboard view with comprehensive statistics and filtering
    """
    # User profile information
    userprofile = takeinfoUser(response)
    username = userprofile["username"]
    profileuser = userprofile["profile"]
    
    # Get filter parameters
    centre_filter = response.GET.get('centre', '')
    age_filter = response.GET.get('age', '')
    designation_filter = response.GET.get('designation', '')
    institution_filter = response.GET.get('institution', '')
    year_filter = response.GET.get('year', '')
    
    # === UNIVERSITÉ STATISTICS (Main Focus) ===
    universites_queryset = Universite.objects.all()
    
    # Apply filters to universites
    if centre_filter:
        universites_queryset = universites_queryset.filter(universite__centre=centre_filter)
    if designation_filter:
        universites_queryset = universites_queryset.filter(universite__designation=designation_filter)
    if institution_filter:
        universites_queryset = universites_queryset.filter(universite__institution=institution_filter)
    if age_filter:
        if age_filter == '18-21':
            start_date, end_date = get_age_range(18, 21)
            universites_queryset = universites_queryset.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            universites_queryset = universites_queryset.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '26-30':
            start_date, end_date = get_age_range(26, 30)
            universites_queryset = universites_queryset.filter(universite__date_naissance__range=[start_date, end_date])
        elif age_filter == '31+':
            end_date = date.today().replace(year=date.today().year - 31)
            universites_queryset = universites_queryset.filter(universite__date_naissance__lte=end_date)
    
    # Basic counts
    total_universites = universites_queryset.count()
    male_count = universites_queryset.filter(universite__genre='M').count()
    female_count = universites_queryset.filter(universite__genre='F').count()
    
    # Designation statistics
    designation_stats = universites_queryset.values('universite__designation').annotate(count=Count('universite__designation')).order_by('-count')
    
    # Institution statistics
    institution_stats = universites_queryset.values('universite__institution').annotate(count=Count('universite__institution')).order_by('-count')
    
    # Centre statistics
    centre_stats = universites_queryset.values('universite__centre').annotate(count=Count('universite__centre')).order_by('-count')
    
    # Age groups calculation
    age_groups = {'18-21': 0, '22-25': 0, '26-30': 0, '31+': 0}
    for univ in universites_queryset:
        if univ.universite and univ.universite.date_naissance:
            age = univ.universite.Age()
            if 18 <= age <= 21:
                age_groups['18-21'] += 1
            elif 22 <= age <= 25:
                age_groups['22-25'] += 1
            elif 26 <= age <= 30:
                age_groups['26-30'] += 1
            else:
                age_groups['31+'] += 1
    
    # === SORTANTS STATISTICS (For Bilan Section) ===
    sortants_queryset = Sortant.objects.all()
    
    # Sortant statistics
    total_sortants_dash = sortants_queryset.count()
    sortant_status_stats_dash = sortants_queryset.values('status').annotate(count=Count('status')).order_by('-count')
    sortant_placement_stats_dash = sortants_queryset.values('placement_type').annotate(count=Count('placement_type')).order_by('-count')
    sortant_poste_stats_dash = sortants_queryset.values('poste_actuel').annotate(count=Count('poste_actuel')).order_by('-count')
    sortant_entreprise_stats_dash = sortants_queryset.values('entreprise').annotate(count=Count('entreprise')).order_by('-count')
    
    # Combined statistics
    total_combined_su = total_universites + total_sortants_dash
    
    # Université additional statistics for Bilan
    universite_filiere_stats_dash = universites_queryset.values('universite__fillier').annotate(count=Count('universite__fillier')).order_by('-count')
    universite_institution_stats_dash = universites_queryset.values('universite__institution').annotate(count=Count('universite__institution')).order_by('-count')
    universite_class_stats_dash = universites_queryset.values('universite__Class').annotate(count=Count('universite__Class')).order_by('-count')
    universite_centre_stats_dash = universites_queryset.values('universite__centre').annotate(count=Count('universite__centre')).order_by('-count')
    
    # Get unique values for filters
    centres = Etudiant.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True)
    designations = Etudiant.objects.values_list('designation', flat=True).distinct().exclude(designation__isnull=True)
    institutions = Etudiant.objects.values_list('institution', flat=True).distinct().exclude(institution__isnull=True)
    
    context = {
        'username': username,
        'profileuser': profileuser,
        'total_universites': total_universites,
        'male_count': male_count,
        'female_count': female_count,
        'designation_stats': designation_stats,
        'institution_stats': institution_stats,
        'centre_stats': centre_stats,
        'age_groups': age_groups,
        'age_18_21': age_groups['18-21'],
        'age_22_25': age_groups['22-25'],
        'age_26_30': age_groups['26-30'],
        'age_31_plus': age_groups['31+'],
        'centres': centres,
        'designations': designations,
        'institutions': institutions,
        'centre_filter': centre_filter,
        'age_filter': age_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'year_filter': year_filter,
        # Bilan Sortants & Université data
        'total_sortants_dash': total_sortants_dash,
        'sortant_status_stats_dash': sortant_status_stats_dash,
        'sortant_placement_stats_dash': sortant_placement_stats_dash,
        'sortant_poste_stats_dash': sortant_poste_stats_dash,
        'sortant_entreprise_stats_dash': sortant_entreprise_stats_dash,
        'total_combined_su': total_combined_su,
        'universite_filiere_stats_dash': universite_filiere_stats_dash,
        'universite_institution_stats_dash': universite_institution_stats_dash,
        'universite_class_stats_dash': universite_class_stats_dash,
        'universite_centre_stats_dash': universite_centre_stats_dash,
    }
    return render(response, "main/universite_dashboard.html", context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def notesuniversite(request):
    """
    Notes Universités view - shows notes for university students with designations
    """
    # Get filter parameters
    search_query = request.GET.get('search', '')
    centre_filter = request.GET.get('centre', '')
    designation_filter = request.GET.get('designation', '')
    institution_filter = request.GET.get('institution', '')
    class_filter = request.GET.get('class', '')
    decision_filter = request.GET.get('decision', '')
    note_range_filter = request.GET.get('note_range', '')
    annee_filter = request.GET.get('annee', '')
    
    # Get university students and their notes
    # First get all university students
    universite_students = Universite.objects.select_related('universite').all()
    
    # Get notes for university students
    notes = NoteEtudiant.objects.filter(
        identifiant__in=[u.universite for u in universite_students]
    ).select_related('identifiant')
    
    # Store original queryset for statistics
    original_notes = notes
    total_notes = original_notes.count()
    
    # Apply filters
    if search_query:
        notes = notes.filter(
            Q(identifiant__nom__icontains=search_query) |
            Q(identifiant__identifiant__icontains=search_query) |
            Q(identifiant__telephone__icontains=search_query)
        )
    
    if centre_filter:
        notes = notes.filter(identifiant__centre=centre_filter)
    
    if designation_filter:
        notes = notes.filter(identifiant__designation=designation_filter)
    
    if institution_filter:
        notes = notes.filter(identifiant__institution=institution_filter)
    
    if class_filter:
        notes = notes.filter(identifiant__Class=class_filter)
    
    if decision_filter:
        notes = notes.filter(decision=decision_filter)
    
    if note_range_filter:
        min_note, max_note = map(float, note_range_filter.split('-'))
        notes = notes.filter(moyen__gte=min_note, moyen__lte=max_note)
    
    if annee_filter:
        notes = notes.filter(annee=annee_filter)
    
    # Calculate statistics
    filtered_count = notes.count()
    
    # Grade distribution statistics
    grade_ranges = {
        '0-8': original_notes.filter(moyen__lt=8).count(),
        '8-10': original_notes.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': original_notes.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': original_notes.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': original_notes.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': original_notes.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': original_notes.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # Decision statistics
    decision_stats = original_notes.values('decision').annotate(count=Count('decision')).order_by('-count')
    
    # Designation statistics
    designation_stats = original_notes.values('identifiant__designation').annotate(count=Count('identifiant__designation')).order_by('-count')
    
    # Institution statistics
    institution_stats = original_notes.values('identifiant__institution').annotate(count=Count('identifiant__institution')).order_by('-count')
    
    # Centre statistics
    centre_stats = original_notes.values('identifiant__centre').annotate(count=Count('identifiant__centre')).order_by('-count')
    
    # Class statistics
    class_stats = original_notes.values('identifiant__Class').annotate(count=Count('identifiant__Class')).order_by('-count')
    
    # Year statistics
    year_stats = original_notes.values('annee').annotate(count=Count('annee')).order_by('-annee')
    
    # Get unique values for filters
    centres = Etudiant.objects.filter(
        universite__isnull=False
    ).values_list('centre', flat=True).distinct().exclude(centre__isnull=True)
    
    designations = Etudiant.objects.filter(
        universite__isnull=False
    ).values_list('designation', flat=True).distinct().exclude(designation__isnull=True)
    
    institutions = Etudiant.objects.filter(
        universite__isnull=False
    ).values_list('institution', flat=True).distinct().exclude(institution__isnull=True)
    
    classes = Etudiant.objects.filter(
        universite__isnull=False
    ).values_list('Class', flat=True).distinct().exclude(Class__isnull=True)
    
    decisions = NoteEtudiant.decisionchoix
    annees = NoteEtudiant.objects.filter(
        identifiant__universite__isnull=False
    ).values_list('annee', flat=True).distinct().exclude(annee__isnull=True).order_by('-annee')
    
    # Pagination
    paginator = Paginator(notes, 15)
    page_number = request.GET.get('page')
    notes = paginator.get_page(page_number)
    
    context = {
        'notes': notes,
        'total_notes': total_notes,
        'filtered_count': filtered_count,
        'grade_ranges': grade_ranges,
        'decision_stats': decision_stats,
        'designation_stats': designation_stats,
        'institution_stats': institution_stats,
        'centre_stats': centre_stats,
        'class_stats': class_stats,
        'year_stats': year_stats,
        'search_query': search_query,
        'centre_filter': centre_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'class_filter': class_filter,
        'decision_filter': decision_filter,
        'note_range_filter': note_range_filter,
        'annee_filter': annee_filter,
        'centres': centres,
        'designations': designations,
        'institutions': institutions,
        'classes': classes,
        'decisions': decisions,
        'annees': annees,
    }
    return render(request, 'main/notesuniversite.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def international(request):
    """
    International students view - shows international students with their details
    """
    # User profile information
    userprofile = takeinfoUser(request)
    username = userprofile["username"]
    profileuser = userprofile["profile"]
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    pays_filter = request.GET.get('pays', '')
    centre_filter = request.GET.get('centre', '')
    fillier_filter = request.GET.get('fillier', '')
    designation_filter = request.GET.get('designation', '')
    institution_filter = request.GET.get('institution', '')
    class_filter = request.GET.get('class', '')
    
    # Get international students
    international_students = International.objects.select_related('international').all()
    
    # Apply filters
    if search_query:
        international_students = international_students.filter(
            Q(international__nom__icontains=search_query) |
            Q(international__identifiant__icontains=search_query) |
            Q(international__telephone__icontains=search_query) |
            Q(international__email__icontains=search_query)
        )
    
    if pays_filter:
        international_students = international_students.filter(pays=pays_filter)
    
    if centre_filter:
        center_values = get_center_filter_values(centre_filter)
        international_students = international_students.filter(international__centre__in=center_values)
    
    if fillier_filter:
        international_students = international_students.filter(international__fillier=fillier_filter)
    
    if designation_filter:
        international_students = international_students.filter(international__designation=designation_filter)
    
    if institution_filter:
        international_students = international_students.filter(international__institution=institution_filter)
    
    if class_filter:
        international_students = international_students.filter(international__Class=class_filter)
    
    # Pagination
    paginator = Paginator(international_students, 20)  # Show 20 students per page
    page_number = request.GET.get('page')
    try:
        students = paginator.page(page_number)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)
    
    # Statistics
    total_international = International.objects.count()
    total_filtered = international_students.count()
    
    # Country statistics
    pays_stats = International.objects.values('pays').annotate(count=Count('pays')).order_by('-count')
    
    # Centre statistics
    centre_stats = International.objects.values('international__centre').annotate(count=Count('international__centre')).order_by('-count')
    
    # Academic statistics
    fillier_stats = International.objects.values('international__fillier').annotate(count=Count('international__fillier')).order_by('-count')
    designation_stats = International.objects.values('international__designation').annotate(count=Count('international__designation')).order_by('-count')
    institution_stats = International.objects.values('international__institution').annotate(count=Count('international__institution')).order_by('-count')
    class_stats = International.objects.values('international__Class').annotate(count=Count('international__Class')).order_by('-count')
    
    # Get unique values for filters
    pays_choices = [choice[0] for choice in International.pays_choice]
    centres = Etudiant.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True)
    filliers = Etudiant.objects.values_list('fillier', flat=True).distinct().exclude(fillier__isnull=True).exclude(fillier='')
    designations = [choice[0] for choice in Etudiant.designationchoice]
    institutions = Etudiant.objects.values_list('institution', flat=True).distinct().exclude(institution__isnull=True).exclude(institution='')
    classes = [choice[0] for choice in Etudiant.batchchoice]
    
    context = {
        'username': username,
        'profileuser': profileuser,
        'students': students,
        'total_international': total_international,
        'total_filtered': total_filtered,
        'pays_stats': pays_stats,
        'centre_stats': centre_stats,
        'fillier_stats': fillier_stats,
        'designation_stats': designation_stats,
        'institution_stats': institution_stats,
        'class_stats': class_stats,
        'pays_choices': pays_choices,
        'centres': centres,
        'filliers': filliers,
        'designations': designations,
        'institutions': institutions,
        'classes': classes,
        'search_query': search_query,
        'pays_filter': pays_filter,
        'centre_filter': centre_filter,
        'fillier_filter': fillier_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'class_filter': class_filter,
    }
    
    return render(request, 'main/international.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def archived_universites(request):
    """
    Archived Universités view - shows archived university students
    """
    # Get archived university students with Archive information
    archived_universites_qs = Archive.objects.filter(archive_type='Université').select_related('archive')
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    centre_filter = request.GET.get('centre', '')
    designation_filter = request.GET.get('designation', '')
    institution_filter = request.GET.get('institution', '')
    archive_type_filter = request.GET.get('archive_type', '')
    raison_filter = request.GET.get('raison', '')
    
    # Apply filters
    if search_query:
        archived_universites_qs = archived_universites_qs.filter(
            Q(archive__nom__icontains=search_query) |
            Q(archive__identifiant__icontains=search_query) |
            Q(archive__telephone__icontains=search_query) |
            Q(archive__institution__icontains=search_query) |
            Q(archive__ville__icontains=search_query) |
            Q(archive__fillier__icontains=search_query)
        )
    if centre_filter:
        center_values = get_center_filter_values(centre_filter)
        archived_universites_qs = archived_universites_qs.filter(archive__centre__in=center_values)
    if designation_filter:
        archived_universites_qs = archived_universites_qs.filter(archive__designation=designation_filter)
    if institution_filter:
        archived_universites_qs = archived_universites_qs.filter(archive__institution=institution_filter)
    if archive_type_filter:
        archived_universites_qs = archived_universites_qs.filter(archive_type=archive_type_filter)
    if raison_filter:
        archived_universites_qs = archived_universites_qs.filter(raison=raison_filter)
    
    # Get unique values for filters
    centres = Etudiant.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True)
    designations = Etudiant.objects.values_list('designation', flat=True).distinct().exclude(designation__isnull=True)
    institutions = Etudiant.objects.values_list('institution', flat=True).distinct().exclude(institution__isnull=True)
    
    # Get archive choices
    archive_choices = [choice[0] for choice in Archive.archive_choice]
    raison_choices = [choice[0] for choice in Archive.raison_choix]
    
    # Pagination
    paginator = Paginator(archived_universites_qs, 15)
    page_number = request.GET.get('page')
    archived_universites = paginator.get_page(page_number)
    
    context = {
        'archived_universites': archived_universites,
        'search_query': search_query,
        'centre_filter': centre_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'archive_type_filter': archive_type_filter,
        'raison_filter': raison_filter,
        'centres': centres,
        'designations': designations,
        'institutions': institutions,
        'archive_choices': archive_choices,
        'raison_choices': raison_choices,
    }
    return render(request, 'main/archived_universites.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def sortant(request):
    """Comprehensive Sortant view with filtering, statistics, and pagination"""
    sortants = Sortant.objects.select_related('sortant').all()
    
    # Store original queryset for statistics
    original_sortants = Sortant.objects.select_related('sortant').all()
    total_sortants = original_sortants.count()

    # Get the filters
    search_query = request.GET.get('search', '')
    center_filter = request.GET.get('centre', '')
    placement_filter = request.GET.get('placement', '')
    genre_filter = request.GET.get('genre', '')
    status_filter = request.GET.get('status', '')
    statut_matrimonial_filter = request.GET.get('statut_matrimonial', '')
    age_filter = request.GET.get('age', '')
    ville_filter = request.GET.get('ville', '')
    # New filters
    poste_filter = request.GET.get('poste', '')
    entreprise_filter = request.GET.get('entreprise', '')
    lieu_travail_filter = request.GET.get('lieu_travail', '')
    date_embauche_filter = request.GET.get('date_embauche', '')
    has_email_filter = request.GET.get('has_email', '')
    orphelin_filter = request.GET.get('orphelin', '')

    # Apply filters
    if search_query:
        sortants = sortants.filter(sortant__nom__icontains=search_query)
    if center_filter:
        centre_values = get_center_filter_values(center_filter)
        if centre_values:
            sortants = sortants.filter(sortant__centre__in=centre_values)
        else:
            sortants = sortants.filter(sortant__centre=center_filter)
    if placement_filter:
        sortants = sortants.filter(placement_type=placement_filter)
    if genre_filter:
        sortants = sortants.filter(sortant__genre=genre_filter)
    if status_filter:
        sortants = sortants.filter(status=status_filter)
    if statut_matrimonial_filter:
        sortants = sortants.filter(statut_matrimonial=statut_matrimonial_filter)
    if ville_filter:
        sortants = sortants.filter(sortant__ville=ville_filter)
    if poste_filter:
        sortants = sortants.filter(poste_actuel=poste_filter)
    if entreprise_filter:
        sortants = sortants.filter(entreprise=entreprise_filter)
    if lieu_travail_filter:
        sortants = sortants.filter(lieu_travail=lieu_travail_filter)
    if date_embauche_filter:
        sortants = sortants.filter(date_embauche__year=date_embauche_filter)
    if has_email_filter:
        if has_email_filter == 'yes':
            sortants = sortants.exclude(sortant__telephone__isnull=True).exclude(sortant__telephone='')
        elif has_email_filter == 'no':
            sortants = sortants.filter(
                Q(sortant__telephone__isnull=True) | Q(sortant__telephone='')
            )
    if orphelin_filter:
        if orphelin_filter == 'yes':
            sortants = sortants.filter(sortant__orphelin__isnull=False)
        elif orphelin_filter == 'no':
            sortants = sortants.filter(sortant__orphelin__isnull=True)

    # Apply age filter based on the categories
    if age_filter:
        if age_filter == '18-21':
            start_date, end_date = get_age_range(18, 21)
            sortants = sortants.filter(sortant__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            sortants = sortants.filter(sortant__date_naissance__range=[start_date, end_date])
        elif age_filter == '26-30':
            start_date, end_date = get_age_range(26, 30)
            sortants = sortants.filter(sortant__date_naissance__range=[start_date, end_date])
        elif age_filter == '31+':
            end_date = date.today().replace(year=date.today().year - 31)
            sortants = sortants.filter(sortant__date_naissance__lte=end_date)

    # Calculate statistics
    filtered_count = sortants.count()
    
    # Gender statistics
    male_count = original_sortants.filter(sortant__genre='M').count()
    female_count = original_sortants.filter(sortant__genre='F').count()
    male_percentage = round((male_count / total_sortants * 100), 1) if total_sortants > 0 else 0
    female_percentage = round((female_count / total_sortants * 100), 1) if total_sortants > 0 else 0
    
    # Placement statistics
    placement_stats = original_sortants.values('placement_type').annotate(count=Count('placement_type')).order_by('-count')
    
    # Status statistics
    status_stats = original_sortants.values('status').annotate(count=Count('status')).order_by('-count')
    
    # Ville statistics - update to use adresse_actuelle instead
    ville_stats = original_sortants.values('adresse_actuelle').annotate(count=Count('adresse_actuelle')).order_by('-count').exclude(adresse_actuelle__isnull=True)
    
    # Age group statistics
    age_groups = {'18-21': 0, '22-25': 0, '26-30': 0, '31+': 0}
    for sortant_obj in original_sortants:
        if sortant_obj.sortant and sortant_obj.sortant.date_naissance:
            age = sortant_obj.sortant.Age()
            if 18 <= age <= 21:
                age_groups['18-21'] += 1
            elif 22 <= age <= 25:
                age_groups['22-25'] += 1
            elif 26 <= age <= 30:
                age_groups['26-30'] += 1
            else:
                age_groups['31+'] += 1

    # Pagination
    paginator = Paginator(sortants, 30)  # Show 30 sortants per page
    page_number = request.GET.get('page', 1)  # Default to page 1
    sortants = paginator.get_page(page_number)

    # Get distinct values for filter options
    centers = Etudiant.objects.values_list('centre', flat=True).distinct()
    placements = Sortant.objects.values_list('placement_type', flat=True).distinct()
    genres = Etudiant.objects.values_list('genre', flat=True).distinct()
    statuses = Sortant.objects.values_list('status', flat=True).distinct()
    villes = Etudiant.objects.values_list('ville', flat=True).distinct().exclude(ville__isnull=True)
    # New filter options
    postes = Sortant.objects.values_list('poste_actuel', flat=True).distinct().exclude(poste_actuel__isnull=True).exclude(poste_actuel='')
    entreprises = Sortant.objects.values_list('entreprise', flat=True).distinct().exclude(entreprise__isnull=True).exclude(entreprise='')
    lieux_travail = Sortant.objects.values_list('lieu_travail', flat=True).distinct().exclude(lieu_travail__isnull=True).exclude(lieu_travail='')
    annees_embauche = Sortant.objects.filter(date_embauche__isnull=False).dates('date_embauche', 'year').distinct()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # Check if the request is AJAX
        sortant_data = []
        for sortant_obj in sortants:
            sortant_data.append({
                'id': sortant_obj.id,
                'nom': sortant_obj.nom() if sortant_obj.sortant else '',
                'image': sortant_obj.sortant.imageprofile.url if sortant_obj.sortant and sortant_obj.sortant.imageprofile else '',
                'telephone': sortant_obj.telephone() if sortant_obj.sortant else '',
                'genre': sortant_obj.genre() if sortant_obj.sortant else '',
                'age': sortant_obj.sortant.Age() if sortant_obj.sortant else 0,
                'placement_type': sortant_obj.placement_type,
                'status': sortant_obj.status,
                'adresse_actuelle': sortant_obj.adresse_actuelle or '',
                'poste_actuel': sortant_obj.poste_actuel or '',
                'entreprise': sortant_obj.entreprise or '',
                'lieu_travail': sortant_obj.lieu_travail or '',
            })
        return JsonResponse({
            'sortants': sortant_data,
            'has_next': sortants.has_next(),
            'has_previous': sortants.has_previous(),
            'page': page_number,
            'num_pages': paginator.num_pages,
        })

    context = {
        'sortants': sortants,
        'search_query': search_query,
        'centre_filter': center_filter,
        'placement_filter': placement_filter,
        'age_filter': age_filter,
        'genre_filter': genre_filter,
        'status_filter': status_filter,
        'statut_matrimonial_filter': statut_matrimonial_filter,
        'ville_filter': ville_filter,
        'poste_filter': poste_filter,
        'entreprise_filter': entreprise_filter,
        'lieu_travail_filter': lieu_travail_filter,
        'date_embauche_filter': date_embauche_filter,
        'has_email_filter': has_email_filter,
        'orphelin_filter': orphelin_filter,
        'centers': centers,
        'placements': placements,
        'genres': genres,
        'statuses': statuses,
        'villes': villes,
        'postes': postes,
        'entreprises': entreprises,
        'lieux_travail': lieux_travail,
        'annees_embauche': [date.year for date in annees_embauche],
        # Statistics
        'total_sortants': total_sortants,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'placement_stats': placement_stats,
        'status_stats': status_stats,
        'ville_stats': ville_stats,
        'age_groups': age_groups,
    }
    return render(request, 'main/sortant.html', context)

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def viewSortant(request, sortant_id):
    """View individual sortant details"""
    try:
        sortant = get_object_or_404(Sortant.objects.select_related('sortant'), id=sortant_id)
        
        # Calculate additional information
        age = sortant.sortant.Age() if sortant.sortant else 0
        duree_emploi = sortant.duree_emploi()
        est_orphelin = sortant.est_orphelin()
        est_etudiant_enregistre = sortant.est_etudiant_enregistre()
        
        context = {
            'sortant': sortant,
            'age': age,
            'duree_emploi': duree_emploi,
            'est_orphelin': est_orphelin,
            'est_etudiant_enregistre': est_etudiant_enregistre,
        }
        
        return render(request, 'main/viewSortant.html', context)
        
    except Sortant.DoesNotExist:
        messages.error(request, "Sortant non trouvé.")
        return redirect('sortant')
    except Exception as e:
        messages.error(request, f"Erreur lors du chargement du sortant: {str(e)}")
        return redirect('sortant')

def get_student_data(request, student_id):
    student = Etudiant.objects.get(id=student_id)
    date=datetime.now()
    year=date.year
    data = {
        'id': student.id,
        'nom': student.nom,
        'imageprofile': student.imageprofile.url,
        'identifiant': student.identifiant,
        'date_naissance': student.date_naissance,
        'Age': year-student.date_naissance.year,
        'nom_pere': student.nom_pere,
        'nom_mere': student.nom_mere,
        'telephone': student.telephone,
        'telephone_mere': student.telephone_mere,
       
        'designation': student.designation,
        'institution': student.institution,
        'ville': student.ville,
        'fillier': student.fillier,
        'Class': student.Class,
        'centre': student.centre,
        'date_entre': student.date_entre,
        'date_sortie': student.date_sortie,
    }
    return JsonResponse(data)





def studentUpdate(response):
    if response.method=='POST':
        id=response.POST['id']
         
        u=Etudiant.objects.get(id=id)
        
        data= {'id':u.id,'name':u.name,'email':u.email,'date_naissance':u.date_naissance,'etudiantid':u.etudiantid,'telephone':u.telephone,
        'ville':u.ville,'name_pere':u.name_pere,'name_mere':u.name_mere,'designation':u.designation,'institution':u.institution,'fillier':u.fillier,
            'batch':u.batch,'centre':u.centre,'telephone_mere':u.telephone_mere,'sex':u.sex,'date_sortie':u.date_sortie,'date_entre':u.date_entre}
        print("this is",data)
        return JsonResponse({"status":"Saved","data":data})
  
    
@login_required(login_url='loginSingup') 
def studentdelete(response,id):
    u=Etudiant.objects.filter(pk=id)
    u.delete()
    return redirect('student')


def studentSearch(response):
     if response.GET:
        name=response.GET['name']
        u=Etudiant.objects.filter(nom__contains=name).values()
        u=list(u)
        return JsonResponse({"status":"Saved","data":u})
     
def noteSearch(response):
     if response.GET:
        name=response.GET['name']
        print("name",name)
        u=Notes.objects.filter(nom__contains=name).values()
        u=list(u)
        return JsonResponse({"status":"Saved","data":u})
     

def personnelSearch(response):
     if response.GET:
        name=response.GET['name']
        u=Personnel.objects.filter(nom__contains=name).values()
        u=list(u)
        return JsonResponse({"status":"Saved","data":u})
     

def noteFilter(response):
     if response.GET:
         note=response.GET['note']
         # gte , gt;lt , lte
         u=Notes.objects.filter(moyen__gte=note).values()
         u=list(u)
         return JsonResponse({"status":"Saved","data":u})
         
    
def studentGroupby(response):
    if response.GET:
        sex=response.GET['sex']
        center=response.GET['centre']
        designation=response.GET['designation']
        u={"sex":sex,"centre":center,"designation":designation}
        c1=Q(designation__contains=u["designation"])
        c2=Q(genre__contains=u["sex"])
        c3=Q(centre__contains=u["centre"])
        #print(c2)
        ls=list(Etudiant.objects.filter(c1&c2&c3).values())

        #print(ls)
        

        return JsonResponse({"status":"Saved","data":ls})


def orphelinGroupby(response):
    if response.GET:
        sex=response.GET['sex']
        center=response.GET['centre']
        batch=response.GET['batch']
        u={"sex":sex,"centre":center,"batch":batch}
        c1=Q(identifiant__Class__contains=u["batch"])
        c2=Q(identifiant__genre__contains=u["sex"])
        centre_values = get_center_filter_values(u["centre"])
        if centre_values:
            c3=Q(identifiant__centre__in=centre_values)
        else:
            c3=Q(identifiant__centre__contains=u["centre"])
        ls=list(Orphelin.objects.filter(c1&c2&c3).values(
            'id', 'décedé', 'identifiant__nom', 'identifiant__genre',
            'identifiant__centre', 'identifiant__Class', 'identifiant__institution',
            'identifiant__date_naissance', 'identifiant__ville'
        ))

        return JsonResponse({"status":"Saved","data":ls})

def studentFilter(response):
    if response.GET:
        if response.GET['category']=='sex':
            val=response.GET['sex']
            c1=Q(genre__contains=val)
            ls=list(Etudiant.objects.filter(c1).values())
            return JsonResponse({"status":"Saved","data":ls})
        if response.GET['category']=='centre':
            val=response.GET['centre']
            c1=Q(centre__contains=val)
            ls=list(Etudiant.objects.filter(c1).values())
            return JsonResponse({"status":"Saved","data":ls})
        if response.GET['category']=='designation':
            val=response.GET['designation']
            c1=Q(designation__contains=val)
            ls=list(Etudiant.objects.filter(c1).values())
            return JsonResponse({"status":"Saved","data":ls})
        

def PersonnelFilter(response):
    
    if response.GET:
        print(response.GET)
        if response.GET['category']=='sex':
            val=response.GET['sex']
            c1=Q(genre__contains=val)
            ls=list(Personnel.objects.filter(c1).values())
            return JsonResponse({"status":"Saved","data":ls})
        if response.GET['category']=='centre':
            val=response.GET['centre']
            c1=Q(centre__contains=val)
            ls=list(Personnel.objects.filter(c1).values())
            return JsonResponse({"status":"Saved","data":ls})
        if response.GET['category']=='situation':
            val=response.GET['situation']
            c1=Q(situation__contains=val)
            ls=list(Personnel.objects.filter(c1).values())
            return JsonResponse({"status":"Saved","data":ls})
        if response.GET['category']=='section':
            val=response.GET['section']
            c1=Q(section__contains=val)
            ls=list(Personnel.objects.filter(c1).values())
            return JsonResponse({"status":"Saved","data":ls})
            
@login_required(login_url='loginSingup') 
def studentUpload(response):
    if response.method=='POST':
        id=response.POST['id']
        u=Etudiant.objects.get(id=id)
        data={'etudiantid':u.etudiantid}
        return JsonResponse({"status":"Saved","data":data})
    
 
def studentView(response):
    if response.method=='POST':
        id=response.POST['id']
        u=Etudiant.objects.get(id=id)
        etudiant=u.identifiant
        print(etudiant)
        dossier=DossierUpload.objects.filter(identifiant=etudiant)
       
        data=[]
        for d in dossier:
            dat={}
            dat["namefile"]=d.namefile
            dat["id"]=d.identifiant
            dat["file"]=d.file.path 
            dat["name"]=d.file.name
            dat["id"]=d.id
            data.append(dat)
        
        

        return JsonResponse({"status":"Saved","data":list(data)})

def viewdocument(response,id):
    d=DossierUpload.objects.get(pk=id)
    print(d)
    path=d.file.name
    print(path)
    return render(response,'main/viewdocument.html',{'path':path})
    

        
        
        
    

def notesUpdate(response):
    if response.method=='POST':
        id=response.POST['id']
        u=Notes.objects.get(id=id)
        data= {'id':u.id,'name':u.nom,'year':u.annee,'semestre':u.semestre,'moyen':u.moyen,'statut':u.statut,'institution':u.institution,'designation':u.designation,'batch':u.batch,'fillier':u.fillier}
        
        return JsonResponse({"status":"Saved","data":data})
    

def notesdelete(response,id):
    form=NotesRegistration
    u=Notes.objects.filter(pk=id)
    u.delete()
    ls=Notes.objects.values()
    return render(response,"main/notes.html",{"form":form,"ls":ls})
    
           
    





def viewStudent(response,etudiantid):
     ls=Etudiant.objects.get(identifiant=etudiantid) if etudiantid else None
     
     
     # Get notes from NoteEtudiant model only
     new_notes=NoteEtudiant.objects.filter(identifiant=ls).order_by('annee').all()
     
     # Get academic history from HistoriqueEtudiant model
     # This displays the student's academic journey and important events
     historique_etudiant = HistoriqueEtudiant.objects.filter(identifiant=ls).order_by('-date').all()
     
     # Prepare chart data for yearly progression
     yearly_data = []
     semester_data = []
     years = []
     yearly_averages = []
     
     # Process notes for charts
     for note in new_notes:
         years.append(str(note.annee))
         yearly_averages.append(float(note.moyen) if note.moyen else 0)
         
         # Add semester data for line chart
         if note.S1:
             semester_data.append({
                 'year': note.annee,
                 'semester': 'S1',
                 'average': float(note.S1)
             })
         if note.S2:
             semester_data.append({
                 'year': note.annee,
                 'semester': 'S2', 
                 'average': float(note.S2)
             })
         if note.S3:
             semester_data.append({
                 'year': note.annee,
                 'semester': 'S3',
                 'average': float(note.S3)
             })
     
     # Create semester progression data
     semester_labels = []
     semester_scores = []
     for sem_data in semester_data:
         semester_labels.append(f"{sem_data['year']} {sem_data['semester']}")
         semester_scores.append(sem_data['average'])
     
     # Calculate statistics
     total_notes = len(yearly_averages)
     avg_performance = sum(yearly_averages) / total_notes if total_notes > 0 else 0
     best_year = max(yearly_averages) if yearly_averages else 0
     worst_year = min(yearly_averages) if yearly_averages else 0
     
     # Performance trend
     trend = "stable"
     if len(yearly_averages) >= 2:
         if yearly_averages[-1] > yearly_averages[0]:
             trend = "improving"
         elif yearly_averages[-1] < yearly_averages[0]:
             trend = "declining"
     
     # Get presence statistics
     presence=Presence.objects.filter(identifiant__identifiant=etudiantid).values('presence').annotate(dcount=Count('id')).order_by()
     presence_total = Presence.objects.filter(identifiant__identifiant=etudiantid).count()
     presence_present = Presence.objects.filter(identifiant__identifiant=etudiantid, presence='P').count()
     presence_absent = presence_total - presence_present
     presence_percentage = (presence_present / presence_total * 100) if presence_total > 0 else 0
     
     # Get avertissements
     avertissement=Avertissement.objects.filter(identifiant__identifiant=etudiantid)
     avertissement_count = avertissement.count()
     
     # Get progress data
     
     
     # Get dossier documents
     dossiers = DossierUpload.objects.filter(identifiant=ls)
     
     # Calculate age
     today = date.today()
     age = today.year - ls.date_naissance.year - ((today.month, today.day) < (ls.date_naissance.month, ls.date_naissance.day))
     
     # Calculate latest decision from notes
     latest_decision = "Non évalué"
     latest_average = 0
     if new_notes.exists():
         latest_note = new_notes.latest('id')
         latest_decision = latest_note.decision or "Non évalué"
         latest_average = latest_note.moyen or 0
     
     context = {
         'etudiant': ls,
         'new_notes': new_notes,
         'historique_etudiant': historique_etudiant,
         'presence_stats': presence,
         'presence_percentage': round(presence_percentage, 1),
         'presence_total': presence_total,
         'presence_present': presence_present,
         'presence_absent': presence_absent,
         'avertissement': avertissement,
         'avertissement_count': avertissement_count,
         
         'dossiers': dossiers,
         'age': age,
         'latest_decision': latest_decision,
         'latest_average': latest_average,
         # Chart data
         'chart_years': years,
         'chart_yearly_averages': yearly_averages,
         'chart_semester_labels': semester_labels,
         'chart_semester_scores': semester_scores,
         # Statistics
         'avg_performance': round(avg_performance, 2),
         'best_year_score': best_year,
         'worst_year_score': worst_year,
         'performance_trend': trend,
         'total_years': total_notes,
     }
     
     return render(response,'main/viewstudent.html', context)

def viewPersonnel(response,id):
     p = get_object_or_404(Personnel, id=id)
     conges = Conge.objects.filter(identifiant=p).order_by('-date_debut')
     dossiers = DossierPersonnel.objects.filter(identifiant=p)
     
     # Statistics for this specific person
     total_days_off = sum([c.nombre_jours() for c in conges if c.date_debut and c.date_fin])
     
     # Calculate days used per year
     current_year = timezone.now().year
     days_used_this_year = sum([c.nombre_jours() for c in conges if c.date_debut and c.date_debut.year == current_year])
     days_remaining_this_year = max(0, 15 - days_used_this_year)
     
     return render(response,'main/viewpersonnel.html',{
         'p':p, 
         'conges':conges, 
         'dossiers':dossiers,
         'total_days_off': total_days_off,
         'days_used_this_year': days_used_this_year,
         'days_remaining_this_year': days_remaining_this_year,
     })

def viewJamat(response,id):
     jamat = get_object_or_404(Jamat, id=id)
     return render(response,'main/viewjamat.html',{'jamat':jamat})

@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def viewMadrassah(request, id):
    madrassah = Madrassah.objects.filter(madrassahid=id).first()
    if madrassah is None:
        raise Http404("Profil madrassah introuvable")
    return render(request, "main/viewmadrassah.html", {"madrassah": madrassah})

def viewPension(response, id):
    """View detailed information for a specific pension record"""
    try:
        pension = Pension.objects.get(id=id)
        
        # Get related documents
        dossiers = DossierPension.objects.filter(pension=pension)
        
        # Get payment history
        paiements = Paiementpension.objects.filter(pension=pension).order_by('-date_paiement')
        total_paye = paiements.aggregate(total=Sum('montant'))['total'] or 0
        
        # Calculate additional information
        today = date.today()
        pension_duration = None
        if pension.date_pension:
            pension_duration = (today - pension.date_pension).days
        
        # Calculate monthly/yearly pension amounts
        monthly_pension = pension.pension if pension.pension else 0
        yearly_pension = monthly_pension * 12 if monthly_pension else 0
        
        context = {
            'pension': pension,
            'dossiers': dossiers,
            'paiements': paiements,
            'total_paye': total_paye,
            'pension_duration': pension_duration,
            'monthly_pension': monthly_pension,
            'yearly_pension': yearly_pension,
        }
        
        return render(response, 'main/viewpensions.html', context)
        
    except Pension.DoesNotExist:
        return render(response, 'main/viewpensions.html', {'error': 'Pension record not found'})

def personneldelete(response,id):
    u=Personnel.objects.filter(pk=id)
    u.delete()
    return redirect('personnel')

def gestion_conge(request):
    """View to display and filter conges - read only, no create/delete/edit"""
    conges = Conge.objects.all().order_by('-date_debut')
    personnels = Personnel.objects.all()
    
    # Filtering options
    personnel_filter = request.GET.get('personnel')
    statut_filter = request.GET.get('statut')
    year_filter = request.GET.get('year')
    date_debut_filter = request.GET.get('date_debut')
    date_fin_filter = request.GET.get('date_fin')
    
    # Apply filters
    if personnel_filter:
        conges = conges.filter(identifiant_id=personnel_filter)
    
    if statut_filter:
        conges = conges.filter(statut=statut_filter)
    
    if year_filter:
        conges = conges.filter(date_debut__year=year_filter)
    
    if date_debut_filter:
        conges = conges.filter(date_debut__gte=date_debut_filter)
    
    if date_fin_filter:
        conges = conges.filter(date_fin__lte=date_fin_filter)
    
    # Statistics for Congés
    total_conges = conges.count()
    
    # Current leaves (leaves where today is between start and end date)
    today = date.today()
    current_leaves_count = conges.filter(date_debut__lte=today, date_fin__gte=today).count()
    
    # Leave types distribution
    type_stats = conges.values('statut').annotate(count=Count('statut')).order_by('-count')
    
    # Get unique years for filter dropdown
    years = Conge.objects.values_list('date_debut__year', flat=True).distinct().order_by('-date_debut__year')
    
    context = {
        'conges': conges, 
        'personnels': personnels,
        'total_conges': total_conges,
        'current_leaves_count': current_leaves_count,
        'type_stats': type_stats,
        'years': years,
        'current_filters': {
            'personnel': personnel_filter,
            'statut': statut_filter,
            'year': year_filter,
            'date_debut': date_debut_filter,
            'date_fin': date_fin_filter,
        }
    }
    return render(request, 'main/gestion_conge.html', context)



@allowed_permisstion(allowed_roles=['Admin','personnel'])
def viewStudentMinimal(request, etudiantid: str):
    """Render a minimal student detail page without the standard sidebar/layout.

    Look up the student by their identifiant (string) and render a lightweight
    standalone template that focuses on the profile photo and primary fields.
    """
    try:
        student = get_object_or_404(Etudiant, identifiant=etudiantid)

        # Notes and academic history (same as full view)
        new_notes = NoteEtudiant.objects.filter(identifiant=student).order_by('annee').all()
        historique_etudiant = HistoriqueEtudiant.objects.filter(identifiant=student).order_by('-date').all()

        # Charts data (computed but not necessarily graphed in minimal view)
        years: list[str] = []
        yearly_averages: list[float] = []
        semester_data: list[dict] = []
        for note in new_notes:
            years.append(str(note.annee))
            yearly_averages.append(float(note.moyen) if note.moyen else 0)
            if note.S1:
                semester_data.append({'year': note.annee, 'semester': 'S1', 'average': float(note.S1)})
            if note.S2:
                semester_data.append({'year': note.annee, 'semester': 'S2', 'average': float(note.S2)})
            if note.S3:
                semester_data.append({'year': note.annee, 'semester': 'S3', 'average': float(note.S3)})

        semester_labels = [f"{d['year']} {d['semester']}" for d in semester_data]
        semester_scores = [d['average'] for d in semester_data]

        total_notes = len(yearly_averages)
        avg_performance = sum(yearly_averages) / total_notes if total_notes > 0 else 0
        best_year = max(yearly_averages) if yearly_averages else 0
        worst_year = min(yearly_averages) if yearly_averages else 0

        trend = "stable"
        if len(yearly_averages) >= 2:
            if yearly_averages[-1] > yearly_averages[0]:
                trend = "improving"
            elif yearly_averages[-1] < yearly_averages[0]:
                trend = "declining"

        # Presence stats
        presence = Presence.objects.filter(identifiant__identifiant=etudiantid).values('presence').annotate(dcount=Count('id')).order_by()
        presence_total = Presence.objects.filter(identifiant__identifiant=etudiantid).count()
        presence_present = Presence.objects.filter(identifiant__identifiant=etudiantid, presence='P').count()
        presence_absent = presence_total - presence_present
        presence_percentage = (presence_present / presence_total * 100) if presence_total > 0 else 0

        # Avertissements and dossiers
        avertissement = Avertissement.objects.filter(identifiant__identifiant=etudiantid)
        avertissement_count = avertissement.count()
        dossiers = DossierUpload.objects.filter(identifiant=student)

        # Age
        age_years = None
        if getattr(student, 'date_naissance', None):
            today = date.today()
            age_years = today.year - student.date_naissance.year - (
                (today.month, today.day) < (student.date_naissance.month, student.date_naissance.day)
            )

        # Latest decision
        latest_decision = "Non évalué"
        latest_average = 0
        if new_notes.exists():
            latest_note = new_notes.latest('id')
            latest_decision = latest_note.decision or "Non évalué"
            latest_average = latest_note.moyen or 0

        context = {
            'student': student,
            'age': age_years,
            'new_notes': new_notes,
            'historique_etudiant': historique_etudiant,
            'dossiers': dossiers,
            'latest_decision': latest_decision,
            'latest_average': latest_average,
            'presence_stats': presence,
            'presence_percentage': round(presence_percentage, 1),
            'presence_total': presence_total,
            'presence_present': presence_present,
            'presence_absent': presence_absent,
            'avertissement': avertissement,
            'avertissement_count': avertissement_count,
            'chart_years': years,
            'chart_yearly_averages': yearly_averages,
            'chart_semester_labels': semester_labels,
            'chart_semester_scores': semester_scores,
            'avg_performance': round(avg_performance, 2),
            'best_year_score': best_year,
            'worst_year_score': worst_year,
            'performance_trend': trend,
            'total_years': total_notes,
        }
        return render(request, 'main/viewstudent_minimal.html', context)
    except Http404:
        messages.error(request, "Étudiant introuvable.")
        return redirect('student')
    except Exception as exc:
        messages.error(request, f"Erreur lors du chargement de l'étudiant: {exc}")
        return redirect('student')


@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def notes(request):
    notes = NoteEtudiant.objects.all()
    
    # Store original queryset for statistics
    original_notes = NoteEtudiant.objects.all()
    total_notes = original_notes.count()
    
    datahead = ['identifiant', 'S1', 'S2', 'S3', 'annee', 'moyen',"rang",'decision','designation','Class','institution']

    # Get the filters from the request
    search_query = request.GET.get('search', '')
    class_filter = request.GET.get('class', '')
    designation_filter = request.GET.get('designation', '')
    institution_filter = request.GET.get('institution', '')
    decision_filter = request.GET.get('decision', '')
    note_range_filter = request.GET.get('note_range', '')
    annee_filter = request.GET.get('annee', '')

    # Apply the filters
    if search_query:
        notes = notes.filter(identifiant__nom__icontains=search_query)
    
    if class_filter:
        notes = notes.filter(identifiant__Class=class_filter)
    
    if designation_filter:
        notes = notes.filter(identifiant__designation=designation_filter)
    
    if institution_filter:
        notes = notes.filter(identifiant__institution=institution_filter)
    
    if decision_filter:
        notes = notes.filter(decision=decision_filter)
    
    if note_range_filter:
        min_note, max_note = map(float, note_range_filter.split('-'))
        notes = notes.filter(moyen__gte=min_note, moyen__lte=max_note)

    if annee_filter:
        notes = notes.filter(annee=annee_filter)

    # Calculate statistics
    filtered_count = notes.count()
    
    # Grade distribution statistics
    grade_ranges = {
        '0-8': original_notes.filter(moyen__lt=8).count(),
        '8-10': original_notes.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': original_notes.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': original_notes.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': original_notes.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': original_notes.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': original_notes.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # Decision statistics
    decision_stats = original_notes.values('decision').annotate(count=Count('decision')).order_by('-count')
    
    # Institution performance statistics
    institution_performance = original_notes.values('identifiant__institution').annotate(
        count=Count('id'),
        avg_score=Avg('moyen'),
        pass_count=Count('id', filter=Q(moyen__gte=10))
    ).order_by('-avg_score')
    
    # Class performance statistics
    class_performance = original_notes.values('identifiant__Class').annotate(
        count=Count('id'),
        avg_score=Avg('moyen'),
        pass_count=Count('id', filter=Q(moyen__gte=10))
    ).order_by('-avg_score')
    
    # Overall statistics
    avg_score = original_notes.aggregate(Avg('moyen'))['moyen__avg']
    pass_rate = (original_notes.filter(moyen__gte=10).count() / total_notes * 100) if total_notes > 0 else 0
    excellence_rate = (original_notes.filter(moyen__gte=16).count() / total_notes * 100) if total_notes > 0 else 0
    
    # Top performers
    top_performers = original_notes.order_by('-moyen')[:5]

    # Pagination (e.g., 30 notes per page)
    paginator = Paginator(notes, 30)
    page_number = request.GET.get('page', 1)
    notes = paginator.get_page(page_number)

    # Get distinct values for filter dropdowns
    classes = NoteEtudiant.objects.values_list('identifiant__Class', flat=True).distinct()
    designations = NoteEtudiant.objects.values_list('identifiant__designation', flat=True).distinct()
    institutions = NoteEtudiant.objects.values_list('identifiant__institution', flat=True).distinct()
    decisions = NoteEtudiant.objects.values_list('decision', flat=True).distinct()
    annees = NoteEtudiant.objects.values_list('annee', flat=True).distinct()

    # Context to pass to the template
    context = {
        'notes': notes,
        'search_query': search_query,
        'class_filter': class_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'decision_filter': decision_filter,
        'note_range': note_range_filter,
        'annee_filter': annee_filter,
        'classes': classes,
        'designations': designations,
        'institutions': institutions,
        'decisions': decisions,
        'annees': annees,
        "datahead": datahead,
        # Statistics
        'total_notes': total_notes,
        'filtered_count': filtered_count,
        'grade_ranges': grade_ranges,
        'decision_stats': decision_stats,
        'institution_performance': institution_performance,
        'class_performance': class_performance,
        'avg_score': round(avg_score, 2) if avg_score else 0,
        'pass_rate': round(pass_rate, 1),
        'excellence_rate': round(excellence_rate, 1),
        'top_performers': top_performers,
    }

    return render(request, 'main/notes.html', context)


@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def noteorphelin(request):
    """Notes view specifically for orphan students"""
    # Get orphan student IDs
    orphan_student_ids = Orphelin.objects.values_list('identifiant__id', flat=True)
    
    # Filter notes to only include orphan students
    notes = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids)
    
    # Store original queryset for statistics
    original_notes = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids)
    total_notes = original_notes.count()
    
    datahead = ['identifiant', 'S1', 'S2', 'S3', 'annee', 'moyen', "rang", 'decision', 'designation', 'Class', 'institution']

    # Get the filters from the request
    search_query = request.GET.get('search', '')
    class_filter = request.GET.get('class', '')
    designation_filter = request.GET.get('designation', '')
    institution_filter = request.GET.get('institution', '')
    decision_filter = request.GET.get('decision', '')
    note_range_filter = request.GET.get('note_range', '')
    orphan_status_filter = request.GET.get('orphan_status', '')
    annee_filter = request.GET.get('annee', '')
    centre_filter = request.GET.get('centre', '')
    rang_filter = request.GET.get('rang', '')
    genre_filter = request.GET.get('genre', '')
    ville_filter = request.GET.get('ville', '')

    # Apply the filters
    if search_query:
        notes = notes.filter(identifiant__nom__icontains=search_query)
    
    if class_filter:
        notes = notes.filter(identifiant__Class=class_filter)
    
    if designation_filter:
        notes = notes.filter(identifiant__designation=designation_filter)
    
    if institution_filter:
        notes = notes.filter(identifiant__institution=institution_filter)
    
    if decision_filter:
        notes = notes.filter(decision=decision_filter)
    
    if note_range_filter:
        min_note, max_note = map(float, note_range_filter.split('-'))
        notes = notes.filter(moyen__gte=min_note, moyen__lte=max_note)
    
    # Filter by orphan status (deceased parent)
    if orphan_status_filter:
        orphan_ids_with_status = Orphelin.objects.filter(décedé=orphan_status_filter).values_list('identifiant__id', flat=True)
        notes = notes.filter(identifiant__id__in=orphan_ids_with_status)
    
    # Filter by year
    if annee_filter:
        notes = notes.filter(annee=annee_filter)

    # Filter by center
    if centre_filter:
        centre_values = get_center_filter_values(centre_filter)
        if centre_values:
            notes = notes.filter(identifiant__centre__in=centre_values)
        else:
            notes = notes.filter(identifiant__centre=centre_filter)

    # Filter by gender
    if genre_filter:
        notes = notes.filter(identifiant__genre=genre_filter)

    # Filter by city
    if ville_filter:
        notes = notes.filter(identifiant__ville=ville_filter)

    # Filter by rank (predefined buckets)
    if rang_filter:
        if rang_filter == '1':
            notes = notes.filter(rang=1)
        elif rang_filter == '1-3':
            notes = notes.filter(rang__gte=1, rang__lte=3)
        elif rang_filter == '1-10':
            notes = notes.filter(rang__gte=1, rang__lte=10)
        elif rang_filter == 'others':
            notes = notes.filter(Q(rang__gt=10) | Q(rang__isnull=True))
        else:
            # Fallback to exact match if a numeric value is provided
            try:
                notes = notes.filter(rang=int(rang_filter))
            except (TypeError, ValueError):
                pass

    # Calculate statistics
    filtered_count = notes.count()
    
    # Grade distribution statistics
    grade_ranges = {
        '0-8': original_notes.filter(moyen__lt=8).count(),
        '8-10': original_notes.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': original_notes.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': original_notes.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': original_notes.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': original_notes.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': original_notes.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # Decision statistics
    decision_stats = original_notes.values('decision').annotate(count=Count('decision')).order_by('-count')
    
    # Institution performance statistics for orphans
    institution_performance = original_notes.values('identifiant__institution').annotate(
        count=Count('id'),
        avg_score=Avg('moyen'),
        pass_count=Count('id', filter=Q(moyen__gte=10))
    ).order_by('-avg_score')
    
    # Class performance statistics for orphans
    class_performance = original_notes.values('identifiant__Class').annotate(
        count=Count('id'),
        avg_score=Avg('moyen'),
        pass_count=Count('id', filter=Q(moyen__gte=10))
    ).order_by('-avg_score')
    
    # Orphan-specific statistics
    orphan_status_stats = Orphelin.objects.filter(identifiant__id__in=orphan_student_ids).values('décedé').annotate(count=Count('décedé')).order_by('-count')
    
    # Gender statistics for orphans
    orphan_gender_stats = original_notes.values('identifiant__genre').annotate(count=Count('identifiant__genre')).order_by('-count')
    
    # Overall statistics
    avg_score = original_notes.aggregate(Avg('moyen'))['moyen__avg']
    pass_rate = (original_notes.filter(moyen__gte=10).count() / total_notes * 100) if total_notes > 0 else 0
    excellence_rate = (original_notes.filter(moyen__gte=16).count() / total_notes * 100) if total_notes > 0 else 0
    
    # Top performing orphans
    top_performers = original_notes.order_by('-moyen')[:5]

    # Pagination (e.g., 30 notes per page)
    paginator = Paginator(notes, 30)
    page_number = request.GET.get('page', 1)
    notes = paginator.get_page(page_number)

    # Get distinct values for filter dropdowns (from orphan students only)
    classes = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids).values_list('identifiant__Class', flat=True).distinct()
    designations = Orphelin.objects.filter(identifiant__id__in=orphan_student_ids).values_list('identifiant__designation', flat=True).distinct()
    institutions = Orphelin.objects.filter(identifiant__id__in=orphan_student_ids).values_list('identifiant__institution', flat=True).distinct()
    decisions = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids).values_list('decision', flat=True).distinct()
    orphan_statuses = Orphelin.objects.values_list('décedé', flat=True).distinct()
    annees = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids).values_list('annee', flat=True).distinct()
    centres = Orphelin.objects.filter(identifiant__id__in=orphan_student_ids).values_list('identifiant__centre', flat=True).distinct()
    rangs = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids).exclude(rang__isnull=True).values_list('rang', flat=True).distinct().order_by('rang')
    genres = NoteEtudiant.objects.filter(identifiant__id__in=orphan_student_ids).values_list('identifiant__genre', flat=True).distinct()
    villes = Orphelin.objects.filter(identifiant__id__in=orphan_student_ids).values_list('identifiant__ville', flat=True).distinct()

    # Context to pass to the template
    context = {
        'notes': notes,
        'search_query': search_query,
        'class_filter': class_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'decision_filter': decision_filter,
        'note_range': note_range_filter,
        'orphan_status_filter': orphan_status_filter,
        'annee_filter': annee_filter,
        'classes': classes,
        'designations': designations,
        'institutions': institutions,
        'decisions': decisions,
        'orphan_statuses': orphan_statuses,
        'annees': annees,
        'centres': centres,
        'rangs': rangs,
        'genres': genres,
        'villes': villes,
        'centre_filter': centre_filter,
        'rang_filter': rang_filter,
        'genre_filter': genre_filter,
        'ville_filter': ville_filter,
        "datahead": datahead,
        # Statistics
        'total_notes': total_notes,
        'filtered_count': filtered_count,
        'grade_ranges': grade_ranges,
        'decision_stats': decision_stats,
        'institution_performance': institution_performance,
        'class_performance': class_performance,
        'orphan_status_stats': orphan_status_stats,
        'orphan_gender_stats': orphan_gender_stats,
        'avg_score': round(avg_score, 2) if avg_score else 0,
        'pass_rate': round(pass_rate, 1),
        'excellence_rate': round(excellence_rate, 1),
        'top_performers': top_performers,
    }

    return render(request, 'main/noteorphelin.html', context)


@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def elite(request):
    """Elite students view"""
    # Get elite student IDs
    elite_student_ids = Elite.objects.values_list('identifiant__id', flat=True)
    
    # Filter students to only include elite students
    datas = Etudiant.objects.filter(id__in=elite_student_ids)
    
    # Store original queryset for statistics
    original_elites = Etudiant.objects.filter(id__in=elite_student_ids)
    total_elites = original_elites.count()
    
    # Get the filters from the request
    search_query = request.GET.get('search', '')
    centre_filter = request.GET.get('centre', '')
    class_filter = request.GET.get('class', '')
    genre_filter = request.GET.get('genre', '')
    institution_filter = request.GET.get('institution', '')
    decede_filter = request.GET.get('decede', '')
    acte_de_dece = request.GET.get('acte_de_dece', '')
    age_filter = request.GET.get('age', '')
    fillier_filter = request.GET.get('fillier', '')

    # Apply the filters
    if search_query:
        datas = datas.filter(nom__icontains=search_query)
    
    if centre_filter:
        datas = datas.filter(centre=centre_filter)
    
    if class_filter:
        datas = datas.filter(Class=class_filter)
    
    if genre_filter:
        datas = datas.filter(genre=genre_filter)
    
    if institution_filter:
        datas = datas.filter(institution=institution_filter)
    
    if fillier_filter:
        datas = datas.filter(fillier=fillier_filter)

    # Calculate statistics
    filtered_count = datas.count()
    
    # Gender statistics
    male_count = original_elites.filter(genre='M').count()
    female_count = original_elites.filter(genre='F').count()
    male_percentage = round((male_count / total_elites * 100), 1) if total_elites > 0 else 0
    female_percentage = round((female_count / total_elites * 100), 1) if total_elites > 0 else 0
    
    # Age distribution statistics
    orphan_age_groups = {}
    for elite in original_elites:
        try:
            age_value = elite.Age()
            age_range = categorize_age(age_value)
            orphan_age_groups[age_range] = orphan_age_groups.get(age_range, 0) + 1
        except Exception:
            # Skip if age cannot be determined
            continue
    
    # Center statistics
    center_stats = original_elites.values('centre').annotate(count=Count('centre')).order_by('-count')
    
    # Class statistics
    class_stats = original_elites.values('Class').annotate(count=Count('Class')).order_by('-count')
    
    # Institution statistics
    institution_stats = original_elites.values('institution').annotate(count=Count('institution')).order_by('-count')
    
    # Fillier statistics
    fillier_stats = original_elites.values('fillier').annotate(count=Count('fillier')).order_by('-count')

    # Pagination
    paginator = Paginator(datas, 30)
    page_number = request.GET.get('page', 1)
    datas = paginator.get_page(page_number)

    # Get distinct values for filter dropdowns
    centres = Etudiant.objects.filter(id__in=elite_student_ids).values_list('centre', flat=True).distinct()
    classes = Etudiant.objects.filter(id__in=elite_student_ids).values_list('Class', flat=True).distinct()
    institutions = Etudiant.objects.filter(id__in=elite_student_ids).values_list('institution', flat=True).distinct()
    filliers = Etudiant.objects.filter(id__in=elite_student_ids).values_list('fillier', flat=True).distinct()

    # Context to pass to the template
    context = {
        'datas': datas,
        'search_query': search_query,
        'centre_filter': centre_filter,
        'class_filter': class_filter,
        'genre_filter': genre_filter,
        'institution_filter': institution_filter,
        'decede_filter': decede_filter,
        'acte_de_dece': acte_de_dece,
        'age_filter': age_filter,
        'fillier_filter': fillier_filter,
        'centres': centres,
        'classes': classes,
        'institutions': institutions,
        'filliers': filliers,
        # Statistics
        'total_orphelins': total_elites,  # Using same variable name for consistency
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'orphan_age_groups': orphan_age_groups,
        'center_stats': center_stats,
        'class_stats': class_stats,
        'institution_stats': institution_stats,
        'fillier_stats': fillier_stats,
    }

    return render(request, 'main/elite.html', context)


@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def noteelite(request):
    """Notes view specifically for elite students"""
    # Get elite student IDs
    elite_student_ids = Elite.objects.values_list('identifiant__id', flat=True)
    
    # Filter notes to only include elite students
    notes = NoteEtudiant.objects.filter(identifiant__id__in=elite_student_ids)
    
    # Store original queryset for statistics
    original_notes = NoteEtudiant.objects.filter(identifiant__id__in=elite_student_ids)
    total_notes = original_notes.count()
    
    datahead = ['identifiant', 'S1', 'S2', 'S3', 'annee', 'moyen', "rang", 'decision', 'designation', 'Class', 'institution']

    # Get the filters from the request
    search_query = request.GET.get('search', '')
    class_filter = request.GET.get('class', '')
    designation_filter = request.GET.get('designation', '')
    institution_filter = request.GET.get('institution', '')
    decision_filter = request.GET.get('decision', '')
    note_range_filter = request.GET.get('note_range', '')
    elite_status_filter = request.GET.get('elite_status', '')

    # Apply the filters
    if search_query:
        notes = notes.filter(identifiant__nom__icontains=search_query)
    
    if class_filter:
        notes = notes.filter(identifiant__Class=class_filter)
    
    if designation_filter:
        notes = notes.filter(identifiant__designation=designation_filter)
    
    if institution_filter:
        notes = notes.filter(identifiant__institution=institution_filter)
    
    if decision_filter:
        notes = notes.filter(decision=decision_filter)
    
    if note_range_filter:
        min_note, max_note = map(float, note_range_filter.split('-'))
        notes = notes.filter(moyen__gte=min_note, moyen__lte=max_note)

    # Calculate statistics
    filtered_count = notes.count()
    
    # Grade distribution statistics
    grade_ranges = {
        '0-8': original_notes.filter(moyen__lt=8).count(),
        '8-10': original_notes.filter(moyen__gte=8, moyen__lt=10).count(),
        '10-12': original_notes.filter(moyen__gte=10, moyen__lt=12).count(),
        '12-14': original_notes.filter(moyen__gte=12, moyen__lt=14).count(),
        '14-16': original_notes.filter(moyen__gte=14, moyen__lt=16).count(),
        '16-18': original_notes.filter(moyen__gte=16, moyen__lt=18).count(),
        '18-20': original_notes.filter(moyen__gte=18, moyen__lte=20).count(),
    }
    
    # Decision statistics
    decision_stats = original_notes.values('decision').annotate(count=Count('decision')).order_by('-count')
    
    # Institution performance statistics for elites
    institution_performance = original_notes.values('identifiant__institution').annotate(
        count=Count('id'),
        avg_score=Avg('moyen'),
        pass_count=Count('id', filter=Q(moyen__gte=10))
    ).order_by('-avg_score')
    
    # Class performance statistics for elites
    class_performance = original_notes.values('identifiant__Class').annotate(
        count=Count('id'),
        avg_score=Avg('moyen'),
        pass_count=Count('id', filter=Q(moyen__gte=10))
    ).order_by('-avg_score')
    
    # Elite-specific statistics
    elite_status_stats = Elite.objects.filter(identifiant__id__in=elite_student_ids).values('identifiant__designation').annotate(count=Count('identifiant__designation')).order_by('-count')
    
    # Gender statistics for elites
    elite_gender_stats = original_notes.values('identifiant__genre').annotate(count=Count('identifiant__genre')).order_by('-count')
    
    # Overall statistics
    avg_score = original_notes.aggregate(Avg('moyen'))['moyen__avg']
    pass_rate = (original_notes.filter(moyen__gte=10).count() / total_notes * 100) if total_notes > 0 else 0
    excellence_rate = (original_notes.filter(moyen__gte=16).count() / total_notes * 100) if total_notes > 0 else 0
    
    # Top performing elites
    top_performers = original_notes.order_by('-moyen')[:5]

    # Pagination (e.g., 30 notes per page)
    paginator = Paginator(notes, 30)
    page_number = request.GET.get('page', 1)
    notes = paginator.get_page(page_number)

    # Get distinct values for filter dropdowns (from elite students only)
    classes = NoteEtudiant.objects.filter(identifiant__id__in=elite_student_ids).values_list('identifiant__Class', flat=True).distinct()
    designations = Elite.objects.filter(identifiant__id__in=elite_student_ids).values_list('identifiant__designation', flat=True).distinct()
    institutions = Elite.objects.filter(identifiant__id__in=elite_student_ids).values_list('identifiant__institution', flat=True).distinct()
    decisions = NoteEtudiant.objects.filter(identifiant__id__in=elite_student_ids).values_list('decision', flat=True).distinct()
    elite_statuses = Elite.objects.values_list('identifiant__designation', flat=True).distinct()

    # Context to pass to the template
    context = {
        'notes': notes,
        'search_query': search_query,
        'class_filter': class_filter,
        'designation_filter': designation_filter,
        'institution_filter': institution_filter,
        'decision_filter': decision_filter,
        'note_range': note_range_filter,
        'elite_status_filter': elite_status_filter,
        'classes': classes,
        'designations': designations,
        'institutions': institutions,
        'decisions': decisions,
        'elite_statuses': elite_statuses,
        "datahead": datahead,
        # Statistics
        'total_notes': total_notes,
        'filtered_count': filtered_count,
        'grade_ranges': grade_ranges,
        'decision_stats': decision_stats,
        'institution_performance': institution_performance,
        'class_performance': class_performance,
        'elite_status_stats': elite_status_stats,
        'elite_gender_stats': elite_gender_stats,
        'avg_score': round(avg_score, 2) if avg_score else 0,
        'pass_rate': round(pass_rate, 1),
        'excellence_rate': round(excellence_rate, 1),
        'top_performers': top_performers,
    }

    return render(request, 'main/noteelite.html', context)


@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def avertissement(response):
    profile=takephotoUser(response=response)
    image=profile.avatar
    
    if response.method=='POST':
        etudiantid=response.POST.get('etudiantid')
        date=response.POST.get("date")
        raison=response.POST.get("raison")
        
        if response.POST.get("submit")=="Update":
            i=response.POST.get('id')
            Avertissement.objects.filter(pk=i).update(
                date=date,
                raison=raison
            )
        else:
            # Create new avertissement
            try:
                etudiant = Etudiant.objects.get(identifiant=etudiantid)
                Avertissement.objects.create(
                    identifiant=etudiant,
                    date=date,
                    raison=raison
                )
                messages.success(response, "Avertissement créé avec succès!")
            except Etudiant.DoesNotExist:
                messages.error(response, "Étudiant non trouvé!")
            except Exception as e:
                messages.error(response, "Erreur lors de la création de l'avertissement.")
        
        return redirect('avertissement')
        
    ls=Avertissement.objects.all()
    return render(response,"main/avertissement.html",{"ls":ls,"image":image})



def avertissementUpdate(response):
    if response.method=='POST':
        id=response.POST['id']
        u=Avertissement.objects.get(id=id)
        data= {'id':u.id,'name':u.nom,'etudiantid':u.identifiant,'date':u.date,'raison':u.raison}
        return JsonResponse({"status":"Saved","data":data})

    
def avertissementdelete(response,id):
    u=Avertissement.objects.filter(pk=id)
    u.delete()
    return redirect('avertissement') 

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def presence(response):
    profile=takephotoUser(response=response)
    image=profile.avatar
    
    if response.method=='POST':
        etudiantid = response.POST.get('etudiantid')
        date = response.POST.get('date')
        swalat = response.POST.get('swalat')
        presence_status = response.POST.get('presence')
        
        try:
            etudiant = Etudiant.objects.get(identifiant=etudiantid)
            Presence.objects.create(
                identifiant=etudiant,
                date=date,
                swalat=swalat,
                presence=presence_status
            )
            messages.success(response, "Présence enregistrée avec succès!")
        except Etudiant.DoesNotExist:
            messages.error(response, "Étudiant non trouvé!")
        except Exception as e:
            messages.error(response, "Erreur lors de l'enregistrement de la présence.")
            
        return redirect('presence')
        
    ls=Presence.objects.all()
    return render(response,"main/presence.html",{"ls":ls,"image":image})
@login_required(login_url='loginSingup')
@allowed_permisstion(allowed_roles=['Admin', 'personnel'])
def personnel(request):
    personnel = Personnel.objects.all()
    
    # Store original queryset for statistics
    original_personnel = Personnel.objects.all()
    total_personnel = original_personnel.count()

    # Get the filters
    search_query = request.GET.get('search', '')
    travail_filter = request.GET.get('travail', '')
    section_filter = request.GET.get('section', '')
    centre_filter = request.GET.get('centre', '')
    situation_filter = request.GET.get('situation', '')
    
    # Apply filters
    if search_query:
        personnel = personnel.filter(nom__icontains=search_query)  # Filter by name
    if travail_filter:
        personnel = personnel.filter(travail=travail_filter)  # Filter by travail
    if section_filter:
        personnel = personnel.filter(section=section_filter)  # Filter by section
    if centre_filter:
        personnel = personnel.filter(centre=centre_filter)  # Filter by centre
    if situation_filter:
        personnel = personnel.filter(situation=situation_filter)  # Filter by situation

    # Calculate statistics
    filtered_count = personnel.count()
    
    # Gender statistics
    male_count = original_personnel.filter(genre='M').count()
    female_count = original_personnel.filter(genre='F').count()
    male_percentage = round((male_count / total_personnel * 100), 1) if total_personnel > 0 else 0
    female_percentage = round((female_count / total_personnel * 100), 1) if total_personnel > 0 else 0
    
    # Section statistics
    section_stats = original_personnel.values('section').annotate(count=Count('section')).order_by('-count')
    
    # Work statistics
    travail_stats = original_personnel.values('travail').annotate(count=Count('travail')).order_by('-count')
    
    # Center statistics
    center_stats = original_personnel.values('centre').annotate(count=Count('centre')).order_by('-count')
    
    # Situation statistics
    situation_stats = original_personnel.values('situation').annotate(count=Count('situation')).order_by('-count')

    # Pagination
    paginator = Paginator(personnel, 30)  # Show 30 personnel per page
    page_number = request.GET.get('page', 1)  # Default to page 1
    personnel = paginator.get_page(page_number)

    # Get distinct values for filter options
    travaux = Personnel.objects.values_list('travail', flat=True).distinct()
    sections = Personnel.objects.values_list('section', flat=True).distinct()
    centres = Personnel.objects.values_list('centre', flat=True).distinct()
    situations = Personnel.objects.values_list('situation', flat=True).distinct()

    # Define table headers
    datahead = ['ID', 'Nom', 'Travail', 'Section', 'Centre', 'Situation', 'Email', 'Téléphone', 'Date d\'Embauche']

    # Handle AJAX requests for dynamic data loading
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        personnel_data = []
        for person in personnel:
            personnel_data.append({
                'id': person.id,
                'nom': person.nom,
                'travail': person.travail,
                'section': person.section,
                'centre': person.centre,
                'situation': person.situation,
                'email': person.email or ' ',
                'telephone': person.telephone or ' ',
                'date_embauche': person.date_embauche,  # Adjust according to your model
            })
        return JsonResponse({
            'personnel': personnel_data,
            'has_next': personnel.has_next(),
            'has_previous': personnel.has_previous(),
            'page': page_number,
            'num_pages': paginator.num_pages,
        })
    print("section_stats",section_stats)
    # Context to render the template
    context = {
        'personnel': personnel,
        'search_query': search_query,
        'travail_filter': travail_filter,
        'section_filter': section_filter,
        'centre_filter': centre_filter,
        'situation_filter': situation_filter,
        'travaux': travaux,
        'sections': sections,
        'centres': centres,
        'situations': situations,
        'datahead': datahead,
        # Statistics
        'total_personnel': total_personnel,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'section_stats': section_stats,
        'travail_stats': travail_stats,
        'center_stats': center_stats,
        'situation_stats': situation_stats,
    }
    return render(request, 'main/personnel.html', context)

def personnelUpdate(response):
    if response.method=='POST':
        id=response.POST['id']
        u=Personnel.objects.get(id=id)
        data= {'id':u.id,'name':u.name,'email':u.email,'personnelid':u.personnelid,'telephone':u.telephone,'centre':u.centre,
        'section':u.section,'travail':u.travail,'sex':u.sex,'situation':u.situation,'adress':u.adress}
        return JsonResponse({"status":"Saved","data":data})
        
@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def jamat(request):
    jamats = Jamat.objects.all()
    
    # Store original queryset for statistics
    original_jamats = Jamat.objects.all()
    total_jamats = original_jamats.count()
    
    # Get the filters
    search = request.GET.get('search', '')
    centre_filter = request.GET.get('centre', '')
    genre_filter = request.GET.get('genre', '')
    age_filter = request.GET.get('age', '')
    travail_filter = request.GET.get('travail', '')
    adress_filter = request.GET.get('adress', '')
    conversion_year_filter = request.GET.get('conversion_year', '')
    email_filter = request.GET.get('email', '')

    # Apply filters
    if search:
        jamats = jamats.filter(Q(nom__icontains=search) | Q(jamatid__icontains=search))
    
    if centre_filter:
        jamats = jamats.filter(centre=centre_filter)
    
    if genre_filter:
        jamats = jamats.filter(genre=genre_filter)
    
    if age_filter:
        current_year = date.today().year
        if age_filter == '-25':
            jamats = jamats.filter(age__lt=25)
        elif age_filter == '25-35':
            jamats = jamats.filter(age__gte=25, age__lte=35)
        elif age_filter == '36-50':
            jamats = jamats.filter(age__gte=36, age__lte=50)
        elif age_filter == '51+':
            jamats = jamats.filter(age__gt=50)
    
    if travail_filter:
        jamats = jamats.filter(travail=travail_filter)
    
    if adress_filter:
        jamats = jamats.filter(adress=adress_filter)

    if conversion_year_filter:
        jamats = jamats.filter(conversion_year=conversion_year_filter)
    
    if email_filter:
        if email_filter == 'yes':
            jamats = jamats.exclude(email__isnull=True).exclude(email='')
        elif email_filter == 'no':
            jamats = jamats.filter(Q(email__isnull=True) | Q(email=''))

    # Calculate statistics
    filtered_count = jamats.count()
    
    # Gender statistics
    male_count = original_jamats.filter(genre='M').count()
    female_count = original_jamats.filter(genre='F').count()
    male_percentage = round((male_count / total_jamats * 100), 1) if total_jamats > 0 else 0
    female_percentage = round((female_count / total_jamats * 100), 1) if total_jamats > 0 else 0
    
    # Contact statistics
    with_contact = original_jamats.filter(telephone__isnull=False).exclude(telephone='').count()
    contact_percentage = round((with_contact / total_jamats * 100), 1) if total_jamats > 0 else 0
    
    # Center statistics
    center_stats = original_jamats.values('centre').annotate(count=Count('centre')).order_by('-count')
    
    # Work statistics
    work_stats = original_jamats.values('travail').annotate(count=Count('travail')).order_by('-count')
    
    # Location statistics
    location_stats = original_jamats.values('adress').annotate(count=Count('adress')).order_by('-count')
    
    # Age group statistics for jamats
    jamat_age_groups = {'-25': 0, '25-35': 0, '36-50': 0, '51+': 0}
    for jamat in original_jamats:
        age = jamat.age
        if age < 25:
            jamat_age_groups['-25'] += 1
        elif 25 <= age <= 35:
            jamat_age_groups['25-35'] += 1
        elif 36 <= age <= 50:
            jamat_age_groups['36-50'] += 1
        else:
            jamat_age_groups['51+'] += 1

    # Pagination: Show 30 per page
    lenght_doc = jamats.count()
    paginator = Paginator(jamats, 30)
    page = request.GET.get('page', 1)
    paginated_jamats = paginator.get_page(page)

    page_query = request.GET.copy()
    if 'page' in page_query:
        page_query.pop('page')

    # Get distinct values for filter options
    centres = Jamat.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True).exclude(centre='')
    travails = Jamat.objects.values_list('travail', flat=True).distinct().exclude(travail__isnull=True).exclude(travail='')
    adresses = Jamat.objects.values_list('adress', flat=True).distinct().exclude(adress__isnull=True).exclude(adress='')
    conversion_years = Jamat.objects.values_list('conversion_year', flat=True).distinct().exclude(conversion_year__isnull=True)
    
    context = {
        'jamats': paginated_jamats,
        'has_next': paginated_jamats.has_next(),
        'has_previous': paginated_jamats.has_previous(),
        'page': paginated_jamats.number,
        'num_pages': paginator.num_pages,
        'search': search,
        'centre_filter': centre_filter,
        'genre_filter': genre_filter,
        'age_filter': age_filter,
        'travail_filter': travail_filter,
        'adress_filter': adress_filter,
        'conversion_year_filter': conversion_year_filter,
        'email_filter': email_filter,
        'centres': centres,
        'travails': travails,
        'adresses': adresses,
        'conversion_years': conversion_years,
        'lenght_doc': lenght_doc,
        'page_query': page_query.urlencode(),
        # Statistics
        'total_jamats': total_jamats,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'with_contact': with_contact,
        'contact_percentage': contact_percentage,
        'center_stats': center_stats,
        'work_stats': work_stats,
        'location_stats': location_stats,
        'jamat_age_groups': jamat_age_groups,
    }
   
    return render(request, "main/jamat.html", context)

def madrassahdelete(response,id):
    u=Madrassah.objects.filter(pk=id)
    u.delete()
    return redirect('madrassah')

    
@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def madrassah(request):
    # Base queryset for stats (all madrassah records)
    original_madrassahs = Madrassah.objects.all()
    total_madrassah = original_madrassahs.count()
    male_count = original_madrassahs.filter(genre='M').count()
    female_count = original_madrassahs.filter(genre='F').count()
    male_percentage = round((male_count / total_madrassah * 100), 1) if total_madrassah > 0 else 0
    female_percentage = round((female_count / total_madrassah * 100), 1) if total_madrassah > 0 else 0

    madrassahs = Madrassah.objects.all()

    # Search functionality
    search = request.GET.get('search', '')
    if search:
        madrassahs = madrassahs.filter(
            Q(nom__icontains=search) | 
            Q(madrassahid__icontains=search)
        )
    
    # Filter by centre
    centre_filter = request.GET.get('centre', '')
    if centre_filter:
        madrassahs = madrassahs.filter(centre=centre_filter)
    
    # Filter by genre
    genre_filter = request.GET.get('genre', '')
    if genre_filter:
        madrassahs = madrassahs.filter(genre=genre_filter)
    
    # Filter by age
    age_filter = request.GET.get('age', '')
    if age_filter:
        if age_filter == '-12':
            madrassahs = madrassahs.filter(age__in=['5', '6', '7', '8', '9', '10', '11', '12'])
        elif age_filter == '12-16':
            madrassahs = madrassahs.filter(age__in=['12', '13', '14', '15', '16'])
        elif age_filter == '17-20':
            madrassahs = madrassahs.filter(age__in=['17', '18', '19', '20'])
        elif age_filter == '21+':
            # For ages 21 and above, assuming they could be stored as strings
            age_values = []
            for i in range(21, 100):  # reasonable upper limit
                age_values.append(str(i))
            madrassahs = madrassahs.filter(age__in=age_values)
    
    # Filter by class_madressah
    class_filter = request.GET.get('class_madressah', '')
    if class_filter:
        madrassahs = madrassahs.filter(class_madressah=class_filter)

    filtered_count = madrassahs.count()

    # Get filter options
    centres = Madrassah.objects.values_list('centre', flat=True).distinct().exclude(centre__isnull=True).exclude(centre='')
    classes_madressah = Madrassah.objects.values_list('class_madressah', flat=True).distinct().exclude(class_madressah__isnull=True).exclude(class_madressah='')
    
    # Pagination
    paginator = Paginator(madrassahs, 30)
    page = request.GET.get('page')
    try:
        madrassahs = paginator.page(page)
    except PageNotAnInteger:
        madrassahs = paginator.page(1)
    except EmptyPage:
        madrassahs = paginator.page(paginator.num_pages)

    lenght_doc = madrassahs.paginator.count

    context = {
        'madrassahs': madrassahs,
        'search': search,
        'centre_filter': centre_filter,
        'genre_filter': genre_filter,
        'age_filter': age_filter,
        'class_filter': class_filter,
        'centres': centres,
        'classes_madressah': classes_madressah,
        'lenght_doc': lenght_doc,
        'total_madrassah': total_madrassah,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'filtered_count': filtered_count,
    }

    return render(request, "main/madrassah.html", context)


       
    


def notesGetId(response):
    if response.method=='GET':
        id=response.GET['etudiantid']
        u=Etudiant.objects.filter(etudiantid=id).values()
        
        data={"etudiantid":u[0]["etudiantid"],"name":u[0]["name"],
              "batch":u[0]["batch"],"designation":u[0]["designation"],
              "fillier":u[0]["fillier"],"institution":u[0]["institution"]}
        
        print(data)
        return JsonResponse({"status":"Saved","data":data})
        
      
def avertissementGetId(response):
    if response.method=='GET':
        id=response.GET['etudiantid']
        u=Etudiant.objects.filter(etudiantid=id).values()
        
        data={"etudiantid":u[0]["etudiantid"],"name":u[0]["name"]}
        return JsonResponse({"status":"Saved","data":data})
    

def presenceGetId(response):
    if response.method=='GET':
        id=response.GET['etudiantid']
        u=Etudiant.objects.filter(etudiantid=id).values()
        
        data={"etudiantid":u[0]["etudiantid"],"name":u[0]["name"]}
        return JsonResponse({"status":"Saved","data":data})


    
@login_required(login_url='loginSingup') 
def viewUser(response):
    data=takeinfoUser(response)
     
    return render(response,"main/viewUser.html",data)



    
def takephotoUser(response):
    cureentuser=response.user
    user_id=cureentuser.id
    user=Profile.objects.get(user_id=user_id)
    return user

      
def notesshowstatbatch(sem,year,batch):
    notes=list(Notes.objects.filter(semestre=sem).filter(annee=year).filter(identifiant__Class=batch).values())
    moyen=[n["moyen"] for n in notes]
    names=[n["name"] for n in notes]
    return {"moyen":moyen,"name":names}


def notesshowstatfillier(sem,year,fillier):
    notes=list(Notes.objects.filter(semestre=sem).filter(annee=year).filter(identifiant__fillier=fillier).values())
    moyen=[n["moyen"] for n in notes]
    names=[n["name"] for n in notes]
    return {"moyen":moyen,"name":names}

 

def getPassStat(response):
          if response.GET:
               sem=response.GET["sem"]
               year=response.GET["annee"]
               passlist=Notes.objects.filter(semestre=sem).filter(year=year).values('statut').annotate(dcount=Count('statut'))
               return JsonResponse({"status":"Saved","data":list(passlist)})
          

def getGetbatch(response):
        if response.GET:
               sem=response.GET["sem"]
               year=response.GET["annee"]
               batch=response.GET["batch"]
              
               data=notesshowstatbatch(sem,year,batch)
               
               return JsonResponse({"status":"Saved","data":data})
        
def getGetfillier(response):
        if response.GET:
            
               sem=response.GET["sem"]
               year=response.GET["annee"]
               f=response.GET["fillier"]
              
               data=notesshowstatfillier(sem,year,f)
               
               
               return JsonResponse({"status":"Saved","data":data})
        

 
        

@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def orphelin(request):
    # Annotate each orphelin with number of uploaded documents for the associated student
    orphelins = Orphelin.objects.all().annotate(docs_count=Count('identifiant__dossier', distinct=True))
    
    # Store original queryset for statistics
    original_orphelins = Orphelin.objects.all()
    total_orphelins = original_orphelins.count()
    
    # Get the filters from the request
    search_query = request.GET.get('search', '')
    centre_filter = request.GET.get('centre', '')
    fillier_filter = request.GET.get('fillier', '')
    class_filter = request.GET.get('class', '')
    genre_filter = request.GET.get('genre', '')
    decede_filter = request.GET.get('decede', '')  # Parent's death status filter
    acte_de_dece = request.GET.get('acte_de_dece', '')  # Death certificate filter
    age_filter = request.GET.get('age', '')
    institution_filter = request.GET.get('institution', '')

    # Apply filters
    if search_query:
        orphelins = orphelins.filter(identifiant__nom__icontains=search_query)
    
    if centre_filter:
        centre_values = get_center_filter_values(centre_filter)
        if centre_values:
            orphelins = orphelins.filter(identifiant__centre__in=centre_values)
        else:
            orphelins = orphelins.filter(identifiant__centre=centre_filter)
    
    if fillier_filter:
        orphelins = orphelins.filter(identifiant__fillier=fillier_filter)
    
    if class_filter:
        orphelins = orphelins.filter(identifiant__Class=class_filter)
    
    if genre_filter:
        orphelins = orphelins.filter(identifiant__genre=genre_filter)

    if institution_filter:
        orphelins = orphelins.filter(identifiant__institution=institution_filter)

    if decede_filter:
        orphelins = orphelins.filter(décedé=decede_filter)

    # New document completeness logic filter
    # complete: (status == 'père' and has acte_de_décé) OR (status != 'père' and status != 'non orphelin' and docs_count >= 3)
    # incomplete: (status == 'père' and missing acte_de_décé) OR (status != 'père' and status != 'non orphelin' and docs_count < 3)
    if acte_de_dece == 'complete':
        orphelins = orphelins.filter(
            (
                Q(décedé='père') & ~Q(acte_de_décé__isnull=True) & ~Q(acte_de_décé='')
            ) | (
                ~Q(décedé='père') & ~Q(décedé='non orphelin') & Q(docs_count__gte=3)
            ) | (
                Q(décedé='non orphelin') & Q(docs_count__gte=3)
            )
        )
    elif acte_de_dece == 'incomplete':
        orphelins = orphelins.filter(
            (
                Q(décedé='père') & (Q(acte_de_décé__isnull=True) | Q(acte_de_décé=''))
            ) | (
                ~Q(décedé='père') & ~Q(décedé='non orphelin') & Q(docs_count__lt=3)
            ) | (
                Q(décedé='non orphelin') & Q(docs_count__lt=3)
            )
        )
    
    # Apply age filter based on the categories
    if age_filter:
        if age_filter == '3-10':
            start_date, end_date = get_age_range(3, 10)
            orphelins = orphelins.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '11-14':
            start_date, end_date = get_age_range(11, 14)
            orphelins = orphelins.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '15-18':
            start_date, end_date = get_age_range(15, 18) 
            orphelins = orphelins.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '19-21':
            start_date, end_date = get_age_range(19, 21)
            orphelins = orphelins.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '22-25':
            start_date, end_date = get_age_range(22, 25)
            orphelins = orphelins.filter(identifiant__date_naissance__range=[start_date, end_date])
        elif age_filter == '26+':
            end_date = date.today().replace(year=date.today().year - 26)
            orphelins = orphelins.filter(identifiant__date_naissance__lte=end_date)

    # Calculate statistics
    filtered_count = orphelins.count()
    
    # Gender statistics
    male_count = original_orphelins.filter(identifiant__genre='M').count()
    female_count = original_orphelins.filter(identifiant__genre='F').count()
    male_percentage = round((male_count / total_orphelins * 100), 1) if total_orphelins > 0 else 0
    female_percentage = round((female_count / total_orphelins * 100), 1) if total_orphelins > 0 else 0
    
    # Orphan status statistics
    decede_stats = original_orphelins.values('décedé').annotate(count=Count('décedé')).order_by('-count')
    
    # Center statistics
    center_stats = original_orphelins.values('identifiant__centre').annotate(count=Count('identifiant__centre')).order_by('-count')
    
    # Age group statistics for orphans
    orphan_age_groups = {'-15': 0, '15-18': 0, '19+': 0}
    for orphelin in original_orphelins:
        try:
            if orphelin.identifiant and orphelin.identifiant.date_naissance:
                today = date.today()
                age = today.year - orphelin.identifiant.date_naissance.year - ((today.month, today.day) < (orphelin.identifiant.date_naissance.month, orphelin.identifiant.date_naissance.day))
                if age <= 15:
                    orphan_age_groups['-15'] += 1
                elif 16 <= age <= 18:
                    orphan_age_groups['15-18'] += 1
                else:
                    orphan_age_groups['19+'] += 1
        except (AttributeError, TypeError):
            # Skip if date_naissance is None or invalid
            continue
    
    # Document availability statistics
    with_documents = original_orphelins.exclude(acte_de_décé__isnull=True).exclude(acte_de_décé='').count()
    without_documents = original_orphelins.filter(acte_de_décé__isnull=True).count()
    document_percentage = round((with_documents / total_orphelins * 100), 1) if total_orphelins > 0 else 0
    
    # Institution statistics
    institution_stats = original_orphelins.values('identifiant__institution').annotate(count=Count('identifiant__institution')).order_by('-count')
    
    # Class statistics
    class_stats = original_orphelins.values('identifiant__Class').annotate(count=Count('identifiant__Class')).order_by('-count')

    # Pagination: Show 30 per page
    lenght_doc=len(orphelins)
    paginator = Paginator(orphelins, 30)
    page = request.GET.get('page', 1)
    paginated_orphelins = paginator.get_page(page)

    # Get distinct values for filter options from orphelins only
    centres = Orphelin.objects.values_list('identifiant__centre', flat=True).distinct().exclude(identifiant__centre__isnull=True).exclude(identifiant__centre='')
    filliers = Orphelin.objects.values_list('identifiant__fillier', flat=True).distinct().exclude(identifiant__fillier__isnull=True).exclude(identifiant__fillier='')
    classes = Orphelin.objects.values_list('identifiant__Class', flat=True).distinct().exclude(identifiant__Class__isnull=True).exclude(identifiant__Class='')
    institutions = Orphelin.objects.values_list('identifiant__institution', flat=True).distinct().exclude(identifiant__institution__isnull=True).exclude(identifiant__institution='')
    decedes = Orphelin.objects.values_list('décedé', flat=True).distinct().exclude(décedé__isnull=True).exclude(décedé='')
    
    datahead=["identifiant","Décedé","Date de Naissance","Genre","Nom mère","Nom du Père","telephone_mere","institution","ville","fillier","Class","Centre","Date d' entree","Date de Sortie"]

    context = {
        'datas': paginated_orphelins,  # Add this for the template
        'orphelins': paginated_orphelins,
        'has_next': paginated_orphelins.has_next(),
        'has_previous': paginated_orphelins.has_previous(),
        'page': paginated_orphelins.number,
        'num_pages': paginator.num_pages,
        'search_query': search_query,
        'centre_filter': centre_filter,
        'fillier_filter': fillier_filter,
        'class_filter': class_filter,
        'genre_filter': genre_filter,
        'decede_filter': decede_filter,
        'acte_de_dece': acte_de_dece,
        'age_filter': age_filter,
        'institution_filter': institution_filter,
        'centres': centres,
        'filliers': filliers,
        'classes': classes,
        'institutions': institutions,
        'datahead': datahead,
        'decedes': decedes,
        'lenght_doc': lenght_doc,
        # Statistics
        'total_orphelins': total_orphelins,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'decede_stats': decede_stats,
        'center_stats': center_stats,
        'orphan_age_groups': orphan_age_groups,
        'with_documents': with_documents,
        'without_documents': without_documents,
        'document_percentage': document_percentage,
        'institution_stats': institution_stats,
        'class_stats': class_stats,
    }

    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        ajax_context = {
            'datas': paginated_orphelins,
            'orphelins': paginated_orphelins,
            'total_orphelins': total_orphelins,
            'filtered_count': filtered_count,
            'male_count': male_count,
            'female_count': female_count,
            'male_percentage': male_percentage,
            'female_percentage': female_percentage,
            'decede_stats': decede_stats,
            'center_stats': center_stats,
            'orphan_age_groups': orphan_age_groups,
            'with_documents': with_documents,
            'without_documents': without_documents,
            'document_percentage': document_percentage,
            'institution_stats': institution_stats,
            'class_stats': class_stats,
            'search_query': search_query,
            'centre_filter': centre_filter,
            'fillier_filter': fillier_filter,
            'class_filter': class_filter,
            'genre_filter': genre_filter,
            'decede_filter': decede_filter,
            'age_filter': age_filter,
            'institution_filter': institution_filter,
            'acte_de_dece': acte_de_dece,
            # Filter options for dropdowns
            'centres': centres,
            'filliers': filliers,
            'classes': classes,
            'institutions': institutions,
            'decedes': decedes,
        }
        return render(request, "main/components/TableOrphelin.html", ajax_context)
   
    return render(request,"main/orphelin.html",context)

def orphelinEdit(response):
     if response.method=='POST':
        id=response.POST['id']
         
        u=Orphelin.objects.get(id=id)
        
        data= {'id':u.id,'name':u.nom,'date_naissance':u.date_naissance,'etudiantid':u.identifiant,
        'ville':u.ville,'name_mere':u.nom_mere,'institution':u.institution,
            'batch':u.Class,'centre':u.centre,'telephone_mere':u.telephone_mere,'sex':u.genre,'date_sortie':u.date_sortie,'date_entre':u.date_entre}
        print("this is",data)
        return JsonResponse({"status":"Saved","data":data})
  
def orphelinSearch(response):
     if response.GET:
        name=response.GET['name']
        u=Orphelin.objects.filter(identifiant__nom__contains=name)
        
        lu=[]
        for i in u:
            data= {'id':i.id,'name':i.identifiant.nom,'date_naissance':i.identifiant.date_naissance,'etudiantid':i.identifiant.identifiant,
        'ville':i.identifiant.ville,'name_mere':i.identifiant.nom_mere,'institution':i.identifiant.institution,"imageprofile":i.identifiant.imageprofile.url,
            'batch':i.identifiant.Class,'centre':i.identifiant.centre,'telephone_mere':i.identifiant.telephone_mere,'sex':i.identifiant.genre,'date_entre':i.identifiant.date_entre}
            lu.append(data)
        
        print(lu)    
        return JsonResponse({"status":"Saved","data":lu}) 

def orphelinfilter(response):
    if response.GET:
        if response.GET['category']=='sex':
            val=response.GET['sex']
            c1=Q(identifiant__genre__contains=val)
            ls=list(Orphelin.objects.filter(c1).values(
                'id', 'décedé', 'identifiant__nom', 'identifiant__genre',
                'identifiant__centre', 'identifiant__Class', 'identifiant__institution',
                'identifiant__date_naissance', 'identifiant__ville'
            ))
            return JsonResponse({"status":"Saved","data":ls})
        if response.GET['category']=='centre':
            val=response.GET['centre']
            centre_values = get_center_filter_values(val)
            if centre_values:
                c1=Q(identifiant__centre__in=centre_values)
            else:
                c1=Q(identifiant__centre__contains=val)
            ls=list(Orphelin.objects.filter(c1).values(
                'id', 'décedé', 'identifiant__nom', 'identifiant__genre',
                'identifiant__centre', 'identifiant__Class', 'identifiant__institution',
                'identifiant__date_naissance', 'identifiant__ville'
            ))
            return JsonResponse({"status":"Saved","data":ls})
        if response.GET['category']=='batch':
            val=response.GET['batch']
            c1=Q(identifiant__Class__contains=val)
            ls=list(Orphelin.objects.filter(c1).values(
                'id', 'décedé', 'identifiant__nom', 'identifiant__genre',
                'identifiant__centre', 'identifiant__Class', 'identifiant__institution',
                'identifiant__date_naissance', 'identifiant__ville'
            ))
            return JsonResponse({"status":"Saved","data":ls})
 

def categorize_age(age):
    if 3 <= age <= 10:
        return '3-10'
    elif 11 <= age <= 14:
        return '11-14'
    elif 15 <= age <= 18:
        return '15-18'
    elif 19 <= age <= 21:
        return '19-21'
    elif 22 <= age <= 25:
        return '22-25'
    else:
        return '26+'

def chart_data(request):
    center = request.GET.get('center', None)
    age_distribution = {'3-10': 0, '11-14': 0, '15-18': 0, '19-21': 0, '22-25': 0, '26+': 0}

    # Filter by center if provided
    students = Etudiant.objects.all()
    if center:
        center_values = get_center_filter_values(center)
        students = students.filter(centre__in=center_values)

    for student in students:
        age = student.Age() 
        age_category = categorize_age(age)
        if age_category in age_distribution:
            age_distribution[age_category] += 1

    labels = list(age_distribution.keys())
    data = list(age_distribution.values())

    # Define colors for each bar
    colors = ['rgba(255, 99, 132, 0.6)', 'rgba(54, 162, 235, 0.6)', 'rgba(255, 206, 86, 0.6)',
              'rgba(75, 192, 192, 0.6)', 'rgba(153, 102, 255, 0.6)']
    border_colors = ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)',
                     'rgba(75, 192, 192, 1)', 'rgba(153, 102, 255, 1)']
    
     

    response_data = {
        'labels': labels,
        'data': data,
        'colors': colors,
        'borderColors': border_colors,
    }
     

    return JsonResponse(response_data)

def gender_distribution(request):
    center = request.GET.get('center', '')  # Get the center from the query parameters
    if center:
        center_values = get_center_filter_values(center)
        students = Etudiant.objects.filter(centre__in=center_values)
    else:
        students = Etudiant.objects.all()

    male_count = students.filter(genre='M').count()
    female_count = students.filter(genre='F').count()

    data = {
        'labels': ['M', 'F'],
        'data': [male_count, female_count]
    }

    return JsonResponse(data)

def designation_distribution(request):
    center = request.GET.get("center")
    
    if center:
        center_values = get_center_filter_values(center)
        etudiants = Etudiant.objects.filter(centre__in=center_values)
    else:
        etudiants = Etudiant.objects.all()

    # Count occurrences of each designation
    designation_counts = Counter(etudiant.designation for etudiant in etudiants)
    
    # Fetch all unique designations from the Etudiant model
    all_designations = Etudiant.objects.values_list('designation', flat=True).distinct()

    # Prepare labels and data, ensuring all designations are included
    labels = list(all_designations)
    data = [designation_counts.get(designation, 0) for designation in labels]

    return JsonResponse({"labels": labels, "data": data})

def enrolled_by_institution_distribution(request):
    center = request.GET.get("center")
    
    if center:
        center_values = get_center_filter_values(center)
        etudiants = Etudiant.objects.filter(centre__in=center_values)
    else:
        etudiants = Etudiant.objects.all()

    # Count occurrences of each institution
    institution_counts = Counter(etudiant.institution for etudiant in etudiants)
    
    # Fetch all unique institutions from the Etudiant model
    all_institutions = Etudiant.objects.values_list('institution', flat=True).distinct()

    # Prepare labels and data, ensuring all institutions are included
    labels = list(all_institutions)
    data = [institution_counts.get(institution, 0) for institution in labels]

    return JsonResponse({"labels": labels, "data": data})
    


def pension(request):
    pensions = Pension.objects.all()
    
    # Store original queryset for statistics
    original_pensions = Pension.objects.all()
    total_pensions = original_pensions.count()
    
    search = request.GET.get('search', '')
    genre_filter = request.GET.get('genre', '')
    age_filter = request.GET.get('age', '')
    cause_filter = request.GET.get('cause', '')

    # Apply filters
    if search:
        pensions = pensions.filter(nom__icontains=search)
    
    if genre_filter:
        pensions = pensions.filter(genre=genre_filter)
    
    if cause_filter:
        pensions = pensions.filter(cause__icontains=cause_filter)
    
    if age_filter:
        if age_filter == '-60':
            pensions = pensions.filter(age__lt=60)
        elif age_filter == '60-70':
            pensions = pensions.filter(age__gte=60, age__lte=70)
        elif age_filter == '70+':
            pensions = pensions.filter(age__gt=70)

    # Calculate statistics
    filtered_count = pensions.count()
    
    # Gender statistics
    male_count = original_pensions.filter(genre='M').count()
    female_count = original_pensions.filter(genre='F').count()
    male_percentage = round((male_count / total_pensions * 100), 1) if total_pensions > 0 else 0
    female_percentage = round((female_count / total_pensions * 100), 1) if total_pensions > 0 else 0
    
    # Age group statistics for pensions
    pension_age_groups = {'-60': 0, '60-70': 0, '70+': 0}
    for pension in original_pensions:
        if pension.age:
            age = pension.age
            if age < 60:
                pension_age_groups['-60'] += 1
            elif 60 <= age <= 70:
                pension_age_groups['60-70'] += 1
            else:
                pension_age_groups['70+'] += 1
    
    # Cause statistics
    cause_stats = original_pensions.values('cause').annotate(count=Count('cause')).order_by('-count')
    
    # Average pension amount
    avg_pension = original_pensions.aggregate(avg_pension=Avg('pension'))['avg_pension'] or 0
    total_pension_amount = original_pensions.aggregate(total_pension=Sum('pension'))['total_pension'] or 0
    
    # Children statistics
    avg_children = original_pensions.aggregate(avg_children=Avg('nombre_enfants'))['avg_children'] or 0
    
    # Document availability statistics (using DossierPension)
    with_documents = original_pensions.filter(dossierpension__isnull=False).distinct().count()
    without_documents = total_pensions - with_documents
    document_percentage = round((with_documents / total_pensions * 100), 1) if total_pensions > 0 else 0

    # Pagination: Show 30 per page
    lenght_doc = len(pensions)
    paginator = Paginator(pensions, 30)
    page = request.GET.get('page', 1)
    paginated_pensions = paginator.get_page(page)

    # Get unique values for filters
    causes = Pension.objects.values_list('cause', flat=True).distinct().exclude(cause__isnull=True).exclude(cause='')
    
    datahead = ["nom", "genre", "age", "telephone", "adress", "date_pension", "pension", "cause", "nombre_enfants"]
    
    context = {
        'pensions': paginated_pensions,
        'has_next': paginated_pensions.has_next(),
        'has_previous': paginated_pensions.has_previous(),
        'page': paginated_pensions.number,
        'num_pages': paginator.num_pages,
        'search': search,
        'genre_filter': genre_filter,
        'age_filter': age_filter,
        'cause_filter': cause_filter,
        'causes': causes,
        'datahead': datahead,
        'lenght_doc': lenght_doc,
        # Statistics
        'total_pensions': total_pensions,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'pension_age_groups': pension_age_groups,
        'cause_stats': cause_stats,
        'avg_pension': avg_pension,
        'total_pension_amount': total_pension_amount,
        'avg_children': avg_children,
        'with_documents': with_documents,
        'without_documents': without_documents,
        'document_percentage': document_percentage,
    }
   
    return render(request, "main/pension.html", context)
     

def pensionEdit(response):
    if response.method == 'POST':
        id = response.POST['id']
        
        u = Pension.objects.get(id=id)
        
        data = {
            'id': u.id,
            'nom': u.nom,
            'genre': u.genre,
            'telephone': u.telephone,
            'adress': u.adress,
            'date_pension': u.date_pension,
            'pension': u.pension,
            'cause': u.cause,
            'nombre_enfants': u.nombre_enfants,
            'age': u.age
        }
        print("this is", data)
        return JsonResponse({"status": "Saved", "data": data})

def pensionSearch(response):
    if response.GET:
        name = response.GET['name']
        u = Pension.objects.filter(nom__contains=name)
        
        lu = []
        for i in u:
            data = {
                'id': i.id,
                'nom': i.nom,
                'genre': i.genre,
                'telephone': i.telephone,
                'adress': i.adress,
                'date_pension': i.date_pension,
                'pension': i.pension,
                'cause': i.cause,
                'nombre_enfants': i.nombre_enfants,
                'age': i.age,
                'imageprofile': i.imageprofile.url if i.imageprofile else None
            }
            lu.append(data)
        
        print(lu)    
        return JsonResponse({"status": "Saved", "data": lu}) 

def pensionFilter(response):
    if response.GET:
        if response.GET['category'] == 'genre':
            val = response.GET['genre']
            c1 = Q(genre__contains=val)
            ls = list(Pension.objects.filter(c1).values())
            return JsonResponse({"status": "Saved", "data": ls})
        if response.GET['category'] == 'cause':
            val = response.GET['cause']
            c1 = Q(cause__contains=val)
            ls = list(Pension.objects.filter(c1).values())
            return JsonResponse({"status": "Saved", "data": ls})
        if response.GET['category'] == 'age':
            val = response.GET['age']
            if val == '-60':
                ls = list(Pension.objects.filter(age__lt=60).values())
            elif val == '60-70':
                ls = list(Pension.objects.filter(age__gte=60, age__lte=70).values())
            elif val == '70+':
                ls = list(Pension.objects.filter(age__gt=70).values())
            else:
                ls = list(Pension.objects.all().values())
            return JsonResponse({"status": "Saved", "data": ls})


@login_required(login_url='loginSingup') 
@allowed_permisstion(allowed_roles=['Admin','personnel'])
def cimitiere(request):
    cimitiere_data = Cimitiere.objects.all()
    
    # Store original queryset for statistics
    original_cimitiere = Cimitiere.objects.all()
    total_cimitiere = original_cimitiere.count()
    
    # Get the filters from the request
    search_query = request.GET.get('search', '')
    genre_filter = request.GET.get('genre', '')
    place_filter = request.GET.get('place', '')
    family_filter = request.GET.get('family', '')
    age_filter = request.GET.get('age', '')
    year_filter = request.GET.get('year', '')

    # Apply filters
    if search_query:
        cimitiere_data = cimitiere_data.filter(nom__icontains=search_query)
    
    if genre_filter:
        cimitiere_data = cimitiere_data.filter(genre=genre_filter)
    
    if place_filter:
        cimitiere_data = cimitiere_data.filter(lieu_deces__icontains=place_filter)
    
    if family_filter:
        cimitiere_data = cimitiere_data.filter(famille__icontains=family_filter)
    
    if year_filter:
        cimitiere_data = cimitiere_data.filter(date_deces__year=year_filter)
    
    # Apply age filter based on age at death
    if age_filter:
        if age_filter == '0-10':
            cimitiere_data = cimitiere_data.extra(where=["YEAR(date_deces) - YEAR(date_naissance) BETWEEN 0 AND 10"])
        elif age_filter == '11-20':
            cimitiere_data = cimitiere_data.extra(where=["YEAR(date_deces) - YEAR(date_naissance) BETWEEN 11 AND 20"])
        elif age_filter == '21-40':
            cimitiere_data = cimitiere_data.extra(where=["YEAR(date_deces) - YEAR(date_naissance) BETWEEN 21 AND 40"])
        elif age_filter == '41-60':
            cimitiere_data = cimitiere_data.extra(where=["YEAR(date_deces) - YEAR(date_naissance) BETWEEN 41 AND 60"])
        elif age_filter == '61-80':
            cimitiere_data = cimitiere_data.extra(where=["YEAR(date_deces) - YEAR(date_naissance) BETWEEN 61 AND 80"])
        elif age_filter == '81+':
            cimitiere_data = cimitiere_data.extra(where=["YEAR(date_deces) - YEAR(date_naissance) > 80"])

    # Calculate statistics
    filtered_count = cimitiere_data.count()
    
    # Gender statistics
    male_count = original_cimitiere.filter(genre='M').count()
    female_count = original_cimitiere.filter(genre='F').count()
    male_percentage = round((male_count / total_cimitiere * 100), 1) if total_cimitiere > 0 else 0
    female_percentage = round((female_count / total_cimitiere * 100), 1) if total_cimitiere > 0 else 0
    
    # Place of death statistics
    place_stats = original_cimitiere.values('lieu_deces').annotate(count=Count('lieu_deces')).order_by('-count')
    
    # Family statistics
    family_stats = original_cimitiere.values('famille').annotate(count=Count('famille')).order_by('-count')
    
    # Age group statistics
    age_groups = {'0-10': 0, '11-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81+': 0}
    for person in original_cimitiere:
        if person.date_naissance and person.date_deces:
            age_at_death = person.date_deces.year - person.date_naissance.year
            if 0 <= age_at_death <= 10:
                age_groups['0-10'] += 1
            elif 11 <= age_at_death <= 20:
                age_groups['11-20'] += 1
            elif 21 <= age_at_death <= 40:
                age_groups['21-40'] += 1
            elif 41 <= age_at_death <= 60:
                age_groups['41-60'] += 1
            elif 61 <= age_at_death <= 80:
                age_groups['61-80'] += 1
            elif age_at_death > 80:
                age_groups['81+'] += 1
    
    # Year statistics
    year_stats = original_cimitiere.values('date_deces__year').annotate(count=Count('date_deces__year')).order_by('-date_deces__year')
    
    # Pagination: Show 30 per page
    lenght_doc = len(cimitiere_data)
    paginator = Paginator(cimitiere_data, 30)
    page = request.GET.get('page', 1)
    paginated_cimitiere = paginator.get_page(page)

    # Get distinct values for filter options
    places = Cimitiere.objects.values_list('lieu_deces', flat=True).distinct().exclude(lieu_deces__isnull=True).exclude(lieu_deces='')
    families = Cimitiere.objects.values_list('famille', flat=True).distinct().exclude(famille__isnull=True).exclude(famille='')
    years = Cimitiere.objects.values_list('date_deces__year', flat=True).distinct().exclude(date_deces__isnull=True).order_by('-date_deces__year')
    
    datahead = ["nom", "genre", "date_naissance", "date_deces", "lieu_deces", "famille", "adress", "telephone"]

    context = {
        'datas': paginated_cimitiere,  # Add this for the template
        'cimitiere': paginated_cimitiere,
        'has_next': paginated_cimitiere.has_next(),
        'has_previous': paginated_cimitiere.has_previous(),
        'page': paginated_cimitiere.number,
        'num_pages': paginator.num_pages,
        'search_query': search_query,
        'genre_filter': genre_filter,
        'place_filter': place_filter,
        'family_filter': family_filter,
        'age_filter': age_filter,
        'year_filter': year_filter,
        'places': places,
        'families': families,
        'years': years,
        'datahead': datahead,
        'lenght_doc': lenght_doc,
        # Statistics
        'total_cimitiere': total_cimitiere,
        'filtered_count': filtered_count,
        'male_count': male_count,
        'female_count': female_count,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'place_stats': place_stats,
        'family_stats': family_stats,
        'age_groups': age_groups,
        'year_stats': year_stats,
    }

    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        ajax_context = {
            'datas': paginated_cimitiere,
            'cimitiere': paginated_cimitiere,
            'total_cimitiere': total_cimitiere,
            'filtered_count': filtered_count,
            'male_count': male_count,
            'female_count': female_count,
            'male_percentage': male_percentage,
            'female_percentage': female_percentage,
            'place_stats': place_stats,
            'family_stats': family_stats,
            'age_groups': age_groups,
            'year_stats': year_stats,
            'search_query': search_query,
            'genre_filter': genre_filter,
            'place_filter': place_filter,
            'family_filter': family_filter,
            'age_filter': age_filter,
            'year_filter': year_filter,
            # Filter options for dropdowns
            'places': places,
            'families': families,
            'years': years,
        }
        return render(request, "main/components/TableCimitiere.html", ajax_context)
   
    return render(request, "main/cimitiere.html", context)


def cimitiereEdit(response):
    if response.method == 'POST':
        id = response.POST['id']
        
        u = Cimitiere.objects.get(id=id)
        
        data = {
            'id': u.id,
            'nom': u.nom,
            'genre': u.genre,
            'date_naissance': u.date_naissance,
            'date_deces': u.date_deces,
            'lieu_deces': u.lieu_deces,
            'famille': u.famille,
            'adress': u.adress,
            'telephone': u.telephone
        }
        print("this is", data)
        return JsonResponse({"status": "Saved", "data": data})


def cimitiereSearch(response):
    if response.GET:
        name = response.GET['name']
        u = Cimitiere.objects.filter(nom__contains=name)
        
        lu = []
        for i in u:
            data = {
                'id': i.id,
                'nom': i.nom,
                'genre': i.genre,
                'date_naissance': i.date_naissance,
                'date_deces': i.date_deces,
                'lieu_deces': i.lieu_deces,
                'famille': i.famille,
                'adress': i.adress,
                'telephone': i.telephone,
                'imageprofile': i.imageprofile.url if i.imageprofile else None
            }
            lu.append(data)
        
        print(lu)    
        return JsonResponse({"status": "Saved", "data": lu}) 


def cimitiereFilter(response):
    if response.GET:
        if response.GET['category'] == 'genre':
            val = response.GET['genre']
            c1 = Q(genre__contains=val)
            ls = list(Cimitiere.objects.filter(c1).values())
            return JsonResponse({"status": "Saved", "data": ls})
        if response.GET['category'] == 'place':
            val = response.GET['place']
            c1 = Q(lieu_deces__contains=val)
            ls = list(Cimitiere.objects.filter(c1).values())
            return JsonResponse({"status": "Saved", "data": ls})
        if response.GET['category'] == 'family':
            val = response.GET['family']
            c1 = Q(famille__contains=val)
            ls = list(Cimitiere.objects.filter(c1).values())
            return JsonResponse({"status": "Saved", "data": ls})
        if response.GET['category'] == 'year':
            val = response.GET['year']
            ls = list(Cimitiere.objects.filter(date_deces__year=val).values())
            return JsonResponse({"status": "Saved", "data": ls})


@login_required(login_url='loginSingup') 
def cimitiereDelete(response, id):
    """Delete a cemetery record"""
    try:
        person = Cimitiere.objects.get(pk=id)
        person.delete()
        messages.success(response, f"L'enregistrement de {person.nom} a été supprimé avec succès.")
    except Cimitiere.DoesNotExist:
        messages.error(response, "L'enregistrement n'existe pas.")
    except Exception as e:
        messages.error(response, f"Erreur lors de la suppression: {str(e)}")
    
    return redirect('cimitiere')


@login_required(login_url='loginSingup')
def viewCimitiere(response, id):
    """View detailed information about a cemetery record"""
    try:
        person = get_object_or_404(Cimitiere, id=id)
        
        # Calculate age at death
        age_at_death = None
        if person.date_naissance and person.date_deces:
            age_at_death = person.date_deces.year - person.date_naissance.year
            # More accurate calculation considering month and day
            if (person.date_deces.month, person.date_deces.day) < (person.date_naissance.month, person.date_naissance.day):
                age_at_death -= 1
        
        # Calculate burial duration
        burial_duration = None
        if person.date_deces:
            today = date.today()
            burial_duration = today.year - person.date_deces.year
            if (today.month, today.day) < (person.date_deces.month, person.date_deces.day):
                burial_duration -= 1
        
        # Get related documents
        dossiers = DossierCimitiere.objects.filter(cimitiere=person)
        
        # Additional statistics for this person's family
        family_members = Cimitiere.objects.filter(famille=person.famille).exclude(id=person.id) if person.famille else []
        family_count = family_members.count()
        
        # Place statistics
        same_place_count = Cimitiere.objects.filter(lieu_deces=person.lieu_deces).exclude(id=person.id).count() if person.lieu_deces else 0
        
        # Year statistics
        same_year_count = Cimitiere.objects.filter(date_deces__year=person.date_deces.year).exclude(id=person.id).count() if person.date_deces else 0
        
        context = {
            'person': person,
            'age_at_death': age_at_death,
            'burial_duration': burial_duration,
            'dossiers': dossiers,
            'family_members': family_members,
            'family_count': family_count,
            'same_place_count': same_place_count,
            'same_year_count': same_year_count,
        }
        
        return render(response, 'main/viewcimitiere.html', context)
        
    except Exception as e:
        messages.error(response, f"Erreur lors de l'affichage: {str(e)}")
        return redirect('cimitiere')


def get_cimitiere_data(request, cimitiere_id):
    """Get cemetery data for AJAX requests"""
    try:
        person = Cimitiere.objects.get(id=cimitiere_id)
        
        # Calculate age at death
        age_at_death = None
        if person.date_naissance and person.date_deces:
            age_at_death = person.date_deces.year - person.date_naissance.year
            if (person.date_deces.month, person.date_deces.day) < (person.date_naissance.month, person.date_naissance.day):
                age_at_death -= 1
        
        data = {
            'id': person.id,
            'nom': person.nom,
            'genre': person.genre,
            'imageprofile': person.imageprofile.url if person.imageprofile else '/static/images/avatar.jpg',
            'date_naissance': person.date_naissance.strftime('%Y-%m-%d') if person.date_naissance else None,
            'date_deces': person.date_deces.strftime('%Y-%m-%d') if person.date_deces else None,
            'lieu_deces': person.lieu_deces,
            'famille': person.famille,
            'adress': person.adress,
            'telephone': person.telephone,
            'age_at_death': age_at_death,
                         'burial_duration': person.duree_enterement() if person.date_deces else None,
        }
        return JsonResponse(data)
        
    except Cimitiere.DoesNotExist:
        return JsonResponse({'error': 'Record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
