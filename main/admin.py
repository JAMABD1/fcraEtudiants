from typing import Any
from django.contrib import admin
from django import forms
from django.http import HttpRequest
from .models import Etudiant,Personnel,Jamat,Madrassah,Avertissement,Pension,Paiementpension,DossierPension,Presence,DossierUpload,Profile,ImageUpload,Orphelin,DossierPersonnel,NoteEtudiant

from .models import Cimitiere,DossierCimitiere,HistoriqueEtudiant,Universite,Elite,Sortant,Archive,International,ArchiveJamat,ArchiveMadrassah
from .models import Conge, CenterAlias, addresschoice, get_centre_choices, get_center_filter_values

from django.contrib.sessions.models import Session
from django.db.models import Q,Count
from django.contrib.auth.models import User
from django.utils.html import format_html_join
import json

from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
admin.site.register(Session)





class ProfileAdmin(admin.ModelAdmin):
    list_display=('user','centre','section','telephone')
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            if request.user.is_superuser:
                 kwargs["queryset"] = User.objects.all()
                 return super().formfield_for_foreignkey(db_field, request, **kwargs)
            kwargs["queryset"] = User.objects.filter(username=request.user.username)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class GenderOFilter(SimpleListFilter):
     title = 'Genre'
     parameter_name = 'genre'
     def lookups(self, request, model_admin):
        return (
            ('F','F'),('M','M')
        )
     def queryset(self, request, queryset):
        if self.value()=='M':
            
            return queryset.filter(identifiant__designation='Orphelinat',identifiant__genre='M')
        if self.value()=='F':
            return queryset.filter(identifiant__designation='Orphelinat',identifiant__genre='F')
       
class HasDossierFilter(admin.SimpleListFilter):
    title = 'a un dossier ?'
    parameter_name = 'has_dossier'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Oui'),
            ('no', 'Non'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(identifiant__dossier__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(identifiant__dossier__isnull=True)
        return queryset
class ActeDeDecesFilter(admin.SimpleListFilter):
    title = "Acte de Décès"
    parameter_name = "has_acte"

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Oui'),
            ('no', 'Non'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(acte_de_décé__isnull=False).exclude(acte_de_décé='')
        if self.value() == 'no':
            return queryset.filter(acte_de_décé__isnull=True) | queryset.filter(acte_de_décé='')
        return queryset

class CentreFilter(admin.SimpleListFilter):
    """Custom filter for centre that includes aliases"""
    title = 'Centre'
    parameter_name = 'centre'

    def lookups(self, request, model_admin):
        """Return all main centers and aliases as filter options"""
        # Get all main centers
        centres = []
        for choice in addresschoice:
            centres.append((choice[0], choice[1]))
        
        # Add all aliases - always fetch fresh from database
        try:
            # Force a fresh query to avoid caching issues
            aliases = list(CenterAlias.objects.all().values_list('alias', 'main_center'))
            for alias, main_center in aliases:
                # Format: (alias_value, "Alias (Main Center)")
                centres.append((alias, f"{alias} ({main_center})"))
        except Exception as e:
            # If CenterAlias table doesn't exist or error occurs, just use main centers
            pass
        
        # Sort by display name
        centres.sort(key=lambda x: x[1])
        return centres

    def queryset(self, request, queryset):
        """Filter queryset to include main center and its aliases"""
        if self.value():
            # Get all values to filter (main center + aliases)
            filter_values = get_center_filter_values(self.value())
            if filter_values:
                return queryset.filter(centre__in=filter_values)
        return queryset

class orphelinAdmin(admin.ModelAdmin):
    list_display=('identifiant','Image','nom','genre','décedé','acte_de_décé','get_dossiers','date_naissance','telephone_mere','institution','ville','Class','centre')
    search_fields=('identifiant','identifiant__nom' )
    list_filter=('identifiant','identifiant__Class','identifiant__institution',
                 'identifiant__centre','identifiant__fillier','identifiant__ville',
                 'identifiant__genre','décedé',HasDossierFilter,ActeDeDecesFilter
                 )
    def get_dossiers(self, obj):
        if obj.identifiant:
            dossiers = obj.identifiant.dossier.all()
            return format_html_join(
                '<br>',
                '<a href="{}" target="_blank">{}</a>',
                [(dossier.file.url, dossier.file.name) for dossier in dossiers]
            )
        return "-"
    
    get_dossiers.short_description = "Dossier(s)"


class DossierUploadAdmin(admin.TabularInline):
     model=DossierUpload
     list_display=('namefile')


 

class NoteEtudiantFAdmin(admin.TabularInline):
    model=NoteEtudiant

class AverissementFAdmin(admin.TabularInline):
   model=Avertissement

class HistoriqueEtudiantAdmin(admin.TabularInline):
    model=HistoriqueEtudiant
    list_display=('nom','date_naissance','genre','date','raison')
    search_fields=('nom','date_naissance','genre','date','raison')
    list_filter=('nom','date_naissance','genre','date','raison')

class EtudiantAdminForm(forms.ModelForm):
    """Custom form that includes center aliases in the centre dropdown"""
    
    class Meta:
        model = Etudiant
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use the same choices function as the model - force refresh from database
        if 'centre' in self.fields:
            fresh_choices = get_centre_choices()
            self.fields['centre'].choices = fresh_choices
            # Also set widget choices to ensure dropdown is updated
            if hasattr(self.fields['centre'], 'widget'):
                self.fields['centre'].widget.choices = fresh_choices

class EtudiantAdmin(admin.ModelAdmin):
    form = EtudiantAdminForm
    inlines=[DossierUploadAdmin,NoteEtudiantFAdmin,AverissementFAdmin,HistoriqueEtudiantAdmin]
    list_display=("identifiant","Image","nom","Age","genre","Class","designation","institution","centre","ville","Dossier","telephone","status")
    search_fields=('identifiant','nom')
    list_filter=['identifiant','nom','designation','genre','Class',CentreFilter,'ville','fillier','institution','status']
    readonly_fields = ( 'image_preview',)
    fieldsets = (
        ("Personal Information", {
            'fields': ('image_preview',"identifiant","imageprofile","nom","date_naissance","genre","Class","designation","institution","centre","fillier","ville","telephone","status","date_entre","date_sortie")
        }),
      
       
    )
    def image_preview(self, obj):
        """Show a rounded profile picture in Django Admin."""
        if obj.imageprofile:
            return format_html(
                '<img src="{}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover;"/>',
                obj.imageprofile.url
            )
        return "No Image"
    image_preview.short_description = "Profile Picture"

    

class DossierPersonnelAdmin(admin.TabularInline):
    model=DossierPersonnel

class PersonnelAdminForm(forms.ModelForm):
    """Custom form that includes center aliases in the centre dropdown"""
    
    class Meta:
        model = Personnel
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use the same choices function as the model - force refresh from database
        if 'centre' in self.fields:
            self.fields['centre'].choices = get_centre_choices()
            # Also set widget choices to ensure dropdown is updated
            if hasattr(self.fields['centre'], 'widget'):
                self.fields['centre'].widget.choices = get_centre_choices()
        
class PersonnelAdmin(admin.ModelAdmin):
    form = PersonnelAdminForm
    inlines=[DossierPersonnelAdmin]
    list_display=('Image','identifiant','nom','genre','centre','travail','section','situation','email','adress',"telephone")
    list_filter=('identifiant','genre','centre','travail','section','situation')
    search_fields=['nom']

class MadrassahlAdmin(admin.ModelAdmin):
    list_display=('madrassahid',"Image",'nom','age',"genre",'centre',"adress","class_madressah","class_academic","parent")
    search_fields=['nom']

    list_filter=('madrassahid','age','genre','centre','adress','class_madressah','class_academic')

class GenderFilter(SimpleListFilter):
    title = 'Gender'
    parameter_name = 'genre'
    def lookups(self, request, model_admin):
        return (
           ('M','M'),('F','F')
        )
    def queryset(self, request, queryset):
        if self.value()=='M':
            
            return queryset.filter(identifiant__genre='M')
        if self.value()=='F':
            return queryset.filter(identifiant__genre='F')

class RangFilter(SimpleListFilter):
    title="Rang"
    parameter_name = 'rang'
    def lookups(self, request, model_admin):
        return (
           ('1','Premier'),('1-3','3 première'),('1-5','5 première'),('1-10','10 première')
        )
    def queryset(self, request, queryset):
        if self.value()=='1':
            return queryset.filter(rang=1)
        if self.value()=='1-3':
            return queryset.filter(rang__range=(1,3))
        if self.value()=='1-5':
            return queryset.filter(rang__range=(1,5))
        if self.value()=='1-10':
            return queryset.filter(rang__range=(1,10))

class MoyenFilter(SimpleListFilter):
    title = 'Moyen'
    parameter_name = 'Moyen'
    def lookups(self, request, model_admin):
        return (
           ('10-12','10-12'),('12-14','12-14'),('14-16','14-16'),('16-18','16-18'),('18-20','18-20')
        )
    def queryset(self, request, queryset):
        if self.value()=='10-12':
            return queryset.filter(moyen__range=(10,12))
        if self.value()=='12-14':
            return queryset.filter(moyen__range=(12,14))
        if self.value()=='14-16':
            return queryset.filter(moyen__range=(14,16))
        if self.value()=='16-18':
            return queryset.filter(moyen__range=(16,18))
        if self.value()=='18-20':
            return queryset.filter(moyen__range=(18,20))


class DesignationFilter(SimpleListFilter):
     title = 'Designation'
     parameter_name = 'designation'
     def lookups(self, request, model_admin):
        return (
            ('Universite','Universite'),('Jeune','Jeune'),
    ('Petit','Petit'),('Orphelinat','Orphelinat')
        )
     def queryset(self, request, queryset):
        if self.value()=='Universite':
            print(queryset)
            return queryset.filter(identifiant__designation='Universite')
        if self.value()=='Jeune':
            return queryset.filter(identifiant__designation='Jeune')
        if self.value()=='Petit':
            return queryset.filter(identifiant__designation='Petit')
        if self.value()=='Orphelinat':
            return queryset.filter(identifiant__designation='Orphelinat')

class NotesEtudiantAdmin(admin.ModelAdmin):
    search_fields=['identifiant__nom',"identifiant"]
    list_display=("identifiant",'imageProfile',"nom","Class","S1","S2","S3","annee","moyen","rang","decision","examreussite","notesimage")
    list_filter=('identifiant','identifiant__Class','identifiant__institution',
                 'identifiant__centre','identifiant__fillier','identifiant__ville',"decision","examreussite",
                 'annee',DesignationFilter,GenderFilter,MoyenFilter,RangFilter,"orphelin")


     

class NotesFAdmin(admin.ModelAdmin):
    list_display=('identifiant','notes_img','nom','moyen','semestre','rang','annee','statut','designation','Class','fillier','institution')
    search_fields=['identifiant__nom']
    list_filter=('identifiant','identifiant__Class','identifiant__institution',
                 'identifiant__centre','identifiant__fillier','identifiant__ville',
                 'annee','statut','semestre',DesignationFilter,GenderFilter,MoyenFilter)
    


     

class AverissementAdmin(admin.ModelAdmin):
     list_display=('identifiant','img','nom','date','raison','designation','Class','fillier','institution')
     search_fields=['identifiant__nom']
     list_filter=('identifiant','identifiant__Class','identifiant__institution',
                 'identifiant__centre','identifiant__fillier','identifiant__ville',
                 )

class PresenceAdmin(admin.ModelAdmin):
    list_display=('identifiant','img','nom','date','swalat','presence')
    search_fields=['nom']
    list_filter=('identifiant','identifiant__Class','identifiant__institution',
                 'identifiant__centre','identifiant__fillier','identifiant__ville','presence'
                 )

class JamatAdminForm(forms.ModelForm):
    """Custom form that includes center aliases in the centre dropdown"""
    
    class Meta:
        model = Jamat
        fields = '__all__'

class JamatAdmin(admin.ModelAdmin):
    form = JamatAdminForm
    list_display=('jamatid','Image','nom','genre','age','centre','adress','travail','telephone')
    search_fields=('jamatid','nom','genre','age')
    list_filter=('genre','centre','travail')
    
class ArchiveJamatAdmin(admin.ModelAdmin):
    list_display=('jamat','nom','archive_type','genre','age','conversion_year','telephone','adresse','travail','centre','raison','archived_at')
    search_fields=('jamat__nom','jamat__jamatid')
    list_filter=('archive_type','raison','jamat__genre','jamat__centre','jamat__travail')

class ArchiveMadrassahAdmin(admin.ModelAdmin):
    list_display = ('madrassah', 'archive_type', 'raison', 'archived_at')
    search_fields = ('madrassah__nom', 'madrassah__madrassahid')
    list_filter = ('archive_type', 'raison', 'madrassah__centre', 'madrassah__genre')

class DossierPensionAdmin(admin.TabularInline):
    model=DossierPension

class PensionAdmin(admin.ModelAdmin):
    inlines=[DossierPensionAdmin]
    list_display=('nom','Image','genre','telephone','adress','age','date_pension','pension','cause','nombre_enfants')
    search_fields=('nom','genre','telephone','adress')
    list_filter=('nom','genre','telephone','adress')

class PaiementpensionAdmin(admin.ModelAdmin):
    list_display=('nom','Image','adress','montant','statut','date_paiement')
    search_fields=('nom','date_paiement','montant','statut')
    list_filter=('pension__nom','date_paiement','montant','statut','pension__adress')

class DossierCimitiereAdmin(admin.TabularInline):
    model=DossierCimitiere
    list_display=('namefile','file')

class CimitiereAdmin(admin.ModelAdmin):
    inlines=[DossierCimitiereAdmin]
    list_display=('nom','Image','genre','telephone','adress','date_deces','lieu_deces','famille','duree_enterement','age')
    search_fields=('nom','genre','telephone','adress')
    list_filter=('nom','genre','telephone','adress','date_deces','lieu_deces','famille')

class UniversiteAdmin(admin.ModelAdmin):
    list_display=('universite','Image','nom','genre','telephone','ville','centre','designation','Class','institution','fillier','date_naissance','date_entre','date_sortie')
    search_fields=('nom','universite')
    list_filter=('universite__nom','universite__genre','universite__ville','universite__centre','universite__designation','universite__Class','universite__institution','universite__fillier','universite__date_naissance','universite__date_entre','universite__date_sortie')

class EliteAdmin(admin.ModelAdmin):
    list_display=('identifiant','Image','nom','genre','telephone','ville','centre','designation','Class','institution','fillier','date_naissance','date_entre')
    search_fields=('nom','universite')
    list_filter=('identifiant__nom','identifiant__genre','identifiant__ville','identifiant__centre','identifiant__designation','identifiant__Class','identifiant__institution','identifiant__fillier','identifiant__date_naissance','identifiant__date_entre','identifiant__date_sortie')

class SortantAdmin(admin.ModelAdmin):
    list_display=('Image','get_nom','get_genre','get_telephone','statut_matrimonial','placement_type','poste_actuel','entreprise','lieu_travail','date_embauche','status','get_job_info')
    list_filter=('statut_matrimonial','placement_type','status','sortant__genre','sortant__Class','sortant__institution','sortant__centre')
    search_fields=('sortant__nom','sortant__identifiant','poste_actuel','entreprise','lieu_travail')
    readonly_fields = ('image_preview',)
    
    fieldsets = (
        ("Student Information", {
            'fields': ('image_preview', 'sortant', 'statut_matrimonial')
        }),
        ("Placement Information", {
            'fields': ('placement_type',)
        }),
        ("Job Information", {
            'fields': ('poste_actuel', 'entreprise', 'lieu_travail', 'date_embauche', 'status')
        }),
        ("Current Address", {
            'fields': ('adresse_actuelle',)
        }),
    )
    
    def get_nom(self, obj):
        """Get student name from related Etudiant"""
        return obj.sortant.nom if obj.sortant else "N/A"
    get_nom.short_description = "Nom"
    get_nom.admin_order_field = 'sortant__nom'
    
    def get_genre(self, obj):
        """Get student gender from related Etudiant"""
        return obj.sortant.genre if obj.sortant else "N/A"
    get_genre.short_description = "Genre"
    get_genre.admin_order_field = 'sortant__genre'
    
    def get_telephone(self, obj):
        """Get student phone from related Etudiant"""
        return obj.sortant.telephone if obj.sortant else "N/A"
    get_telephone.short_description = "Téléphone"
    get_telephone.admin_order_field = 'sortant__telephone'
    
    def get_job_info(self, obj):
        """Get formatted job information"""
        return obj.get_job_info()
    get_job_info.short_description = "Informations Emploi"
    
    def image_preview(self, obj):
        """Show a rounded profile picture in Django Admin."""
        if obj.sortant and obj.sortant.imageprofile:
            return format_html(
                '<img src="{}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover;"/>',
                obj.sortant.imageprofile.url
            )
        return "No Image"
    image_preview.short_description = "Photo de Profil"
    
    def Image(self, obj):
        """Display image for list view"""
        if obj.sortant and obj.sortant.imageprofile:
            return format_html('<img src="{}" width="50" height="50"/>', obj.sortant.imageprofile.url)
        return "No Image"
    Image.short_description = "Photo"
     
 
class ArchiveAdmin(admin.ModelAdmin):
    list_display=('archive','image','nom','archive_type','genre','telephone','ville','centre','designation','Class','raison')
    search_fields=('archive__nom','archive__identifiant')
    list_filter=('archive_type','raison','archive__genre','archive__centre','archive__designation','archive__Class','archive__ville')

class InternationalAdmin(admin.ModelAdmin):
    list_display=('international','Image','nom','genre','telephone','ville','centre','designation','Class','pays','duree_sejour','date_depart')
    search_fields=('international__nom','international__identifiant')
    list_filter=('international__genre','international__centre','international__designation','international__Class','international__ville','pays','duree_sejour','date_depart')


class CongeAdmin(admin.ModelAdmin):
    list_display=('get_identifiant','get_nom','get_section','get_travail','raison','statut','date_debut','date_fin','nombre_jours','jours_restants')
    search_fields=('identifiant__nom','identifiant__identifiant')
    list_filter=('statut','identifiant__centre','identifiant__travail')

    def get_identifiant(self, obj):
        return obj.identifiant.identifiant if obj.identifiant else 'N/A'
    get_identifiant.short_description = 'Matricule'
    get_identifiant.admin_order_field = 'identifiant__identifiant'

    def get_nom(self, obj):
        return obj.identifiant.nom if obj.identifiant else 'N/A'
    get_nom.short_description = 'Nom'
    get_nom.admin_order_field = 'identifiant__nom'

    def get_section(self, obj):
        return obj.identifiant.get_section_display() if obj.identifiant else 'N/A'
    get_section.short_description = 'Section'
    get_section.admin_order_field = 'identifiant__section'

    def get_travail(self, obj):
        return obj.identifiant.get_travail_display() if obj.identifiant else 'N/A'
    get_travail.short_description = 'Travail'
    get_travail.admin_order_field = 'identifiant__travail'



   
admin.site.register(International,InternationalAdmin),

admin.site.register(Etudiant,EtudiantAdmin),
admin.site.register(Paiementpension,PaiementpensionAdmin),
admin.site.register(Personnel,PersonnelAdmin),
 

admin.site.register(Jamat,JamatAdmin),
admin.site.register(Madrassah,MadrassahlAdmin),

admin.site.register(Pension,PensionAdmin),


admin.site.register(Avertissement,AverissementAdmin),

admin.site.register(Presence,PresenceAdmin),
# Register your models here.
admin.site.register(ArchiveJamat,ArchiveJamatAdmin),
admin.site.register(ArchiveMadrassah, ArchiveMadrassahAdmin),
admin.site.register(Orphelin,orphelinAdmin),
admin.site.register(NoteEtudiant,NotesEtudiantAdmin),

admin.site.register(Cimitiere,CimitiereAdmin),
admin.site.register(Universite,UniversiteAdmin),
admin.site.register(Elite,EliteAdmin),

admin.site.register(Sortant,SortantAdmin),
admin.site.register(Archive,ArchiveAdmin),

admin.site.register(Conge,CongeAdmin),

class CenterAliasAdmin(admin.ModelAdmin):
    list_display = ('main_center', 'alias')
    list_filter = ('main_center',)
    search_fields = ('main_center', 'alias')
    ordering = ('main_center', 'alias')

admin.site.register(CenterAlias, CenterAliasAdmin)