from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.html import mark_safe
from datetime import datetime
from django.utils import timezone
from django.utils.crypto import get_random_string
import os
 
from django.conf import settings

statuschoice=(('Actif','Actif'),('Inactif','Inactif'),('Sortant','Sortant'))

TYPE_CONGE=(('Maladie','Maladie'),('Famille','Famille'),('Congé','Congé'),('Autre','Autre'))

# Center choices - shared across models
addresschoice=(('Antaniavo','Antaniavo'),('Ankarobato','Ankarobato'),('Manakara','Manakara'),('Andakana','Andakana'),('Sakoana','Sakoana'))

CENTRE_JAMAT_CHOICES=(('Antaniavo','Antaniavo'),('Ankarobato','Ankarobato'),
('Manakara','Manakara'),('Andakana','Andakana'),('Sakoana','Sakoana'),
('ANORONORO','ANORONORO'),('AMBOLOSY','AMBOLOSY'),('AMBARAMBABY','AMBARAMBABY'),
('AMBODINATO','AMBODINATO'),('AMPITSONJOVA','AMPITSONJOVA'),('ANDOHARANO','ANDOHARANO'),
('ANDRANOVATO','ANDRANOVATO'),('AMBOLONAONDRY','AMBOLONAONDRY'),('ANALANJIROFO','ANALANJIROFO'),
('AMBOROBE','AMBOROBE'),('BETSIBAKY','BETSIBAKY'),('BEKATRA','BEKATRA'),
('FANDAVO','FANDAVO'),('FOTSIVAVO','FOTSIVAVO'),('LANIVO IKAIKY','LANIVO IKAIKY'),
('LANIVO FARAFASY','LANIVO FARAFASY'),('LANIVO TSARARY','LANIVO TSARARY'),('LANIVO ANOSY','LANIVO ANOSY'),
('LANIVO MAHAZOARIVO','LANIVO MAHAZOARIVO'),('LIMITE EST','LIMITE EST'),('LIMITE OUEST','LIMITE OUEST'),
('AMBATOMAHAVAGNO','AMBATOMAHAVAGNO'),('MAHASOA VOHIBOLO','MAHASOA VOHIBOLO'),('NAMENA TANAMBAO','NAMENA TANAMBAO'),
('LANIVO CENTRE TANJONDAVA','LANIVO CENTRE TANJONDAVA'),('TAVIHAMBA','TAVIHAMBA'),('VOHIBOLO','VOHIBOLO'),
('VOHIMASINA','VOHIMASINA'),('MITANTY MANAKARA','MITANTY MANAKARA'),('FARAFASY','FARAFASY'),
('AMBALAVARY','AMBALAVARY'),('VATANA','VATANA'),('MITANTY EST','MITANTY EST'),
('AMBOHIMANDROSO','AMBOHIMANDROSO'),('TSARAMANDROSO','TSARAMANDROSO'),('AMBATOHARANA','AMBATOHARANA'),
('ANDRANOBOKA','ANDRANOBOKA'),('AMBATO','AMBATO'),('AMBALAROKA','AMBALAROKA'),
('AMBOHITROVA','AMBOHITROVA'),('AMBODIVOAHANGY','AMBODIVOAHANGY'),('AMBATOMALAGNONA','AMBATOMALAGNONA'),
('AMBAHIBO','AMBAHIBO'),('FANOVIA BETSIRIRY','FANOVIA BETSIRIRY'),('TANAMBAO','TANAMBAO'))

class CenterAlias(models.Model):
    """Model to store aliases for centers"""
    id = models.AutoField(primary_key=True)
    main_center = models.CharField(max_length=100, choices=addresschoice, verbose_name="Centre principal")
    alias = models.CharField(max_length=100, unique=True, verbose_name="Alias")
    
    class Meta:
        verbose_name = "Alias de Centre"
        verbose_name_plural = "Alias de Centres"
        ordering = ['main_center', 'alias']
    
    def __str__(self):
        return f"{self.alias} → {self.main_center}"

def get_centre_choices():
    """
    Returns center choices including main centers and all aliases.
    This function is callable and will be used as choices parameter in model fields.
    """
    # Start with the main center choices
    centre_choices = list(addresschoice)
    
    # Add all aliases to the choices
    try:
        # Import here to avoid circular imports
        from .models import CenterAlias
        aliases = CenterAlias.objects.all().values_list('alias', 'main_center')
        for alias, main_center in aliases:
            # Format: (alias_value, "Alias (Main Center)")
            centre_choices.append((alias, f"{alias} ({main_center})"))
    except Exception as e:
        # If CenterAlias table doesn't exist yet (during migrations), just return main choices
        # Also catch any database errors
        pass
    
    # Sort choices for better UX
    centre_choices.sort(key=lambda x: x[1])
    
    return centre_choices

def get_center_filter_values(center_name):
    """
    Returns a list of center names including the main name and all aliases.
    Used for filtering queries to include aliases.
    """
    if not center_name:
        return []
    
    # Start with the main center name
    values = [center_name]
    
    # Add all aliases for this center
    aliases = CenterAlias.objects.filter(main_center=center_name).values_list('alias', flat=True)
    values.extend(list(aliases))
    
    return values

class Etudiant(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.CharField(max_length=100,unique=True,null=False)
    nom=models.CharField(max_length=100)
    
    date_naissance=models.DateField(verbose_name="Date de Naissance",null=True, blank=True)
    genrechoice=(('M','M'),('F','F'))
    genre=models.CharField(max_length=4,choices=genrechoice,default='M')
    telephone=models.CharField(null=True, blank=True,max_length=20)
    
    nom_pere=models.CharField(max_length=100,null=True, blank=True,verbose_name="Nom du père")
    nom_mere=models.CharField(max_length=100,null=True, blank=True,verbose_name="Nom du mère")
    telephone_mere=models.CharField(null=True, blank=True,max_length=20)
    designationchoice=(('Universite','Universite'),
    ('Jeune','Jeune'),('Elite','Elite'),('International','International'),
    ('Petit','Petit'),('crashcourse','crashcourse'),('internat','internat'),('dine','dine'),('Bachelor Dine','Bachelor Dine'),('Bachelor Université','Bachelor Université')
    )
    designation=models.CharField(max_length=100,choices=designationchoice,default='Jeune')
    fillier=models.CharField(max_length=100,null=True, blank=True)
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='images/')
    institution=models.CharField(max_length=100)
    ville=models.CharField(max_length=100)
    batchchoice=(('PS','PS'),('MS','MS'),('GS','GS'),('CP','CP'),('CE1','CE1'),('CE2','CE2'),
                 ('CM1','CM1'), ('CM2','CM2'),
                 ('6eme','6eme'),('5eme','5eme'),('4eme','4eme'),('3eme','3eme'),
    ('2nd','2nd'),('1ere','1ere'),('Terminal','Terminal'),
        ('1ere annee','1ere annee'),('2eme annee','2eme annee'),('3eme annee','3eme annee'),
    ('4eme annee','4eme annee'),('5eme annee','5eme annee'),('6eme annee','6eme annee')
    )
    Class=models.CharField(max_length=100,choices=batchchoice,default='1ere annee')
    centre=models.CharField(max_length=100,choices=get_centre_choices(),default='Antaniavo')
    status=models.CharField(max_length=100,choices=statuschoice,default='Actif')
    
    date_entre=models.DateField(null=True, blank=True)
    date_sortie=models.DateField(null=True, blank=True)
     

    def __str__(self):
        return self.identifiant
    def Image(self):
        url = self.imageprofile.url if self.imageprofile and self.imageprofile.url else '/media/images/avatar.jpg'
        return mark_safe('<img src="%s" width="50" height="50"/>' % url)
    def Dossier(self):
        from .models import DossierUpload  # Avoid circular imports
        dossiers = DossierUpload.objects.filter(identifiant__identifiant=self.identifiant)
        links = [f'<a target="_blank" style=" color:"blue" " href="{p.file.url}">{p.namefile}</a>' for p in dossiers]
        return mark_safe('<div>' + ", ".join(links) + '</div>')
   

        
    def Age(self):
        date=datetime.now()
        year=0
        try:    
            year=self.date_naissance.year 
        except:
            year=0
        if year==0:
            return 0
        return date.year-year
        
        
         

    def get_absence_count(self):
        """Calculate the number of absences for this student"""
        from .models import Presence  # Avoid circular imports
        total_presence = Presence.objects.filter(identifiant=self).count()
        present_count = Presence.objects.filter(identifiant=self, presence='P').count()
        return total_presence - present_count

class HistoriqueEtudiant(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.ForeignKey(Etudiant,on_delete=models.CASCADE,related_name='historique',null=True,unique=False,verbose_name="Identifiant")
    date=models.DateField(null=True, blank=True)
    raison=models.TextField(null=True, blank=True)
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.identifiant.imageprofile.url))
    def nom(self):
        return self.identifiant.nom
    def date_naissance(self):
        return self.identifiant.date_naissance
    def genre(self):
        return self.identifiant.genre
    def __str__(self):
        return self.identifiant.nom









class Orphelin(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.ForeignKey(Etudiant,on_delete=models.CASCADE,related_name='orphelin',null=True,unique=False,verbose_name="Identifiant")
    décedé=models.CharField(max_length=50,choices=(("mère","mère"),("père","père"),("Orphelin père et mère","Orphelin père et mère"),("non orphelin","non orphelin")),null=True,blank=True,verbose_name="Orphelin")
    acte_de_décé=models.FileField(upload_to="actes/",null=True,blank=True,verbose_name="Acte de décé")
     
    def nom(self):
        return self.identifiant.nom
    def date_naissance(self):
        return self.identifiant.date_naissance
    def genre(self):
        return self.identifiant.genre
    def nom_mere(self):
        return self.identifiant.nom_mere
    def telephone_mere(self):
        return self.identifiant.telephone_mere
    def age(self):
        return self.identifiant.Age()
    
    def institution(self):
        return self.identifiant.institution
    def ville(self):
        return self.identifiant.ville
    def Class(self):
        return self.identifiant.Class
    def centre(self):
        return self.identifiant.centre
    def date_entre(self):
        return self.identifiant.date_entre
    
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.identifiant.imageprofile.url))
    
    

   
    def __str__(self):
        return self.identifiant.nom
    



class ImageUpload(models.Model):
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='images/')

class NotesUpload(models.Model):
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='notes/')

class DossierUpload(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.ForeignKey(Etudiant,on_delete=models.CASCADE,null=True,related_name="dossier")
   
    namefile=models.CharField(max_length=50,default='Dossier')
    file=models.FileField(upload_to='dossier/')
    def __str__(self):
        return self.namefile

class NoteEtudiant(models.Model):
    identifiant=models.ForeignKey(Etudiant,on_delete=models.CASCADE,null=True,related_name="notesetudiant")
    S1=models.DecimalField(  max_digits = 5, decimal_places = 2,null=True, blank=True)
    S2=models.DecimalField(  max_digits = 5, decimal_places = 2,null=True, blank=True)
    S3=models.DecimalField(  max_digits = 5, decimal_places = 2,null=True, blank=True)
    annee=models.CharField(max_length=10,null=True,blank=True)
    moyen=models.DecimalField(  max_digits = 5, decimal_places = 2,null=True, blank=True)
    rang=models.IntegerField(null=True,blank=True)
    decisionchoix=(('Admis','Admis'),('Repechage','Repechage'),('Redouble','Redouble'),('Passable','Passable'),('Assez-bien','Assez-bien'),('Bien','Bien'),('Tres bien','Tres bien'))
    decision=models.CharField(max_length=11,choices=decisionchoix,default='Admis',null=True, blank=True)
    examreussite=models.CharField(max_length=10,choices=(("CEPE","CEPE"),("BEPC","BEPC"),("BAC","BAC")),null=True,blank=True)
    notesimage=models.FileField(default='images/avatar.jpg',null=True,blank=True,upload_to='notes/')
    orhelinchoice=(('Orphelin','Orphelin'),('Etudiant','Etudiant'),('Elite','Elite'))
    orphelin=models.CharField(max_length=11,choices=orhelinchoice,default='Etudiant',null=True, blank=True)
     
    def __str__(self):
        return self.identifiant.nom
    def designation(self):
        return self.identifiant.designation
    def Class(self):
        return self.identifiant.Class
    def fillier(self):
        return self.identifiant.fillier
    def institution(self):
        return self.identifiant.institution
    def nom(self):
        return self.identifiant.nom
    def imageProfile(self):
        return mark_safe('<img src="%s" width="50" height="50"  "/>'% (self.identifiant.imageprofile.url))
    def is_orphelin(self):
        """Check if the associated student is listed in the Orphelin table."""
        return Orphelin.objects.filter(identifiant=self.identifiant).exists()

    def is_elite(self):
        """Check if the associated student is listed in the Elite table."""
        return Elite.objects.filter(identifiant=self.identifiant).exists()

    def save(self, *args, **kwargs):
        """Automatically set the orphelin field before saving."""
        if self.is_orphelin():
            self.orphelin = 'Orphelin'
        elif self.is_elite():
            self.orphelin = 'Elite'
        else:
            self.orphelin = 'Etudiant'
        super().save(*args, **kwargs)
     

 






class Avertissement(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.ForeignKey(Etudiant,on_delete=models.CASCADE)
    date=models.DateField(null=True)
    raison=models.CharField(max_length=100,null=True)
    def __str__(self):
        return self.identifiant.nom
    def __str__(self):
        return self.identifiant.nom
    def designation(self):
        return self.identifiant.designation
    def Class(self):
        return self.identifiant.Class
    def fillier(self):
        return self.identifiant.fillier
    def institution(self):
        return self.identifiant.institution
    def nom(self):
        return self.identifiant.nom

    def img(self):
        return mark_safe('<img src="%s" width="100" height="100"/>'% (self.identifiant.imageprofile.url))
    
    

class Presence(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.ForeignKey(Etudiant,on_delete=models.CASCADE,null=True)
    date=models.DateField(null=True)
    swalatchoice=(('Fajr','Fajr'),('Maghrib','Maghrib'))
    swalat=models.CharField(max_length=10,choices=swalatchoice,default='Fajr')
    presencechoice=(('P','P'),('A','A'))
    presence=models.CharField(max_length=10,choices=presencechoice,default='Fajr')
    def __str__(self):
        return self.identifiant.nom
    def nom(self):
        return self.identifiant.nom
    def img(self):
        return mark_safe('<img src="%s" width="100" height="100"/>'% (self.identifiant.imageprofile.url))
   
   
    



class Personnel(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.CharField(max_length=100, unique=True, verbose_name="matricule")
    nom=models.CharField(max_length=100, verbose_name="Nom complet")
    genrechoice=(('M','Masculin'),('F','Féminin'))
    genre=models.CharField(max_length=5,choices=genrechoice,default='M', verbose_name="Genre")
    telephone=models.CharField(null=True, blank=True,max_length=20, verbose_name="Téléphone")
    
    sectionchoice=(
        ('multimedia','Multimédia'),
        ('cheick','Cheick'),
        ('administration','Administration'),
        ('rvs','RVS'),
        ('securite','Sécurité'),
        ('jardinier','Jardinier'),
        ('technicien','Technicien'),
        ('cuisine','Cuisine'),
        ('proprete','Propreté'),
        ('madressat','Madressat'),
        ('construction','Construction'),
        ('transport','Transport'),
        ('dispensaire','Dispensaire'),
        ('maintenance','Maintenance'),
        ('comptabilite','Comptabilité')
    )
    section=models.CharField(max_length=50,choices=sectionchoice,default='multimedia', verbose_name="Section")
    
    centre=models.CharField(max_length=100,choices=get_centre_choices(),default='Antaniavo', verbose_name="Centre")
    
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='images/', verbose_name="Photo de profil")
    
    travailchoice=(
        ('Enseignant','Enseignant'),
        ('Administrateur','Administrateur'),
        ('Technicien','Technicien'),
        ('Superviseur','Superviseur'),
        ('Coordinateur','Coordinateur'),
        ('Responsable','Responsable'),
        ('Assistant','Assistant'),
        ('Consultant','Consultant'),
        ('Support','Support'),
        ('Maintenance','Maintenance'),
        ('Gardien','Gardien'),
        ('Chauffeur','Chauffeur'),
        ('Cuisinier','Cuisinier'),
        ('Jardinier','Jardinier'),
        ('Nettoyage','Nettoyage')
    )
    travail=models.CharField(max_length=100, choices=travailchoice, default='Assistant', verbose_name="Type de travail")
    
    email=models.EmailField(max_length=100,null=True, blank=True, verbose_name="Email")
    
    situationchoice=(
        ('Actif','Actif'),
        ('Inactif','Inactif'),
        ('En congé','En congé'),
        ('Suspendu','Suspendu'),
        ('Retraité','Retraité')
    )
    #situation=models.CharField(max_length=50,choices=situationchoice,default='Actif', verbose_name="Situation")
    
    statut_matrimonialchoice=(
        ('celibataire','Célibataire'),
        ('marie','Marié(e)'),
        ('veuf','Veuf/Veuve'),
        ('divorce','Divorcé(e)')
    )
    situation=models.CharField(max_length=50,choices=statut_matrimonialchoice,default='celibataire', verbose_name="Statut matrimonial")
    
    adress=models.CharField(max_length=200,null=True, blank=True, verbose_name="Adresse")
    
    class Meta:
        verbose_name = "Personnel"
        verbose_name_plural = "Personnel"
        ordering = ['nom']
        indexes = [
            models.Index(fields=['identifiant']),
            models.Index(fields=['nom']),
            models.Index(fields=['section']),
            models.Index(fields=['centre']),
            models.Index(fields=['situation']),
        ]
    def save(self, *args, **kwargs):
        if not self.identifiant:
            self.identifiant = self.generate_unique_identifiant()
        super().save(*args, **kwargs)

    def generate_unique_identifiant(self):
        prefix = "PER"
        while True:
            random_id = prefix + get_random_string(length=5, allowed_chars='0123456789')
            if not Personnel.objects.filter(identifiant=random_id).exists():
                return random_id
    
    def __str__(self):
        return f"{self.nom} ({self.identifiant})"
    
    def Image(self):
        if self.imageprofile:
            return mark_safe('<img src="%s" width="50" height="50" class="rounded-full"/>' % (self.imageprofile.url))
        return mark_safe('<div class="w-12 h-12 bg-gray-300 rounded-full flex items-center justify-center"><span class="text-gray-600">%s</span></div>' % (self.nom[0].upper() if self.nom else '?'))
    
     
    
   

    
    
    
  
    
    def get_work_type_color(self):
        """Return appropriate CSS class for work type badge"""
        work_colors = {
            'Enseignant': 'bg-green-100 text-green-800',
            'Administrateur': 'bg-blue-100 text-blue-800',
            'Support': 'bg-yellow-100 text-yellow-800',
            'Technicien': 'bg-purple-100 text-purple-800',
            'Superviseur': 'bg-indigo-100 text-indigo-800',
            'Coordinateur': 'bg-pink-100 text-pink-800',
        }
        return work_colors.get(self.travail, 'bg-gray-100 text-gray-800')
    
    def get_remaining_conges(self, year=None):
        """Calculate remaining conge days for this personnel in a given year"""
        if year is None:
            year = timezone.now().year
        
        conges_this_year = Conge.objects.filter(
            identifiant=self,
            date_debut__year=year
        )
        
        total_days = sum(conge.nombre_jours() for conge in conges_this_year if conge.nombre_jours() > 0)
        remaining = 15 - total_days
        return max(0, remaining)
    
class Conge(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.ForeignKey(Personnel,on_delete=models.CASCADE,null=True,verbose_name="matricule")
    date_debut=models.DateField(null=True, blank=True,verbose_name="Date de début")
    date_fin=models.DateField(null=True, blank=True,verbose_name="Date de fin")
    raison=models.TextField(null=True, blank=True,verbose_name="Raison")
    statut=models.CharField(max_length=100,choices=TYPE_CONGE,default='Congé',verbose_name="Type de congé")
    
    def nombre_jours(self):
        """Calculate the number of days for this conge"""
        if not self.date_debut or not self.date_fin:
            return 0
        if self.date_fin < self.date_debut:
            return 0
        return (self.date_fin - self.date_debut).days
    
    def get_total_days_per_year(self, year=None, include_current=False):
        """Calculate total conge days used by this personnel in a given year"""
        if not self.identifiant:
            return 0
        
        if year is None:
            # Use the year of the current conge's start date
            if self.date_debut:
                year = self.date_debut.year
            else:
                year = timezone.now().year
        
        # Get all conges for this personnel in the given year
        conges_this_year = Conge.objects.filter(
            identifiant=self.identifiant,
            date_debut__year=year
        )
        
        # Exclude current conge only if include_current is False (for validation)
        if not include_current:
            conges_this_year = conges_this_year.exclude(id=self.id)
        
        total_days = sum(conge.nombre_jours() for conge in conges_this_year if conge.nombre_jours() > 0)
        return total_days
    
    def jours_restants(self, year=None):
        """Calculate remaining conge days for this personnel in a given year"""
        if not self.identifiant:
            return 15
        
        if year is None:
            if self.date_debut:
                year = self.date_debut.year
            else:
                year = timezone.now().year
        
        # Include current conge in the calculation for display
        total_used = self.get_total_days_per_year(year, include_current=True)
        remaining = 15 - total_used
        return max(0, remaining)  # Don't return negative values
    
    def save(self, *args, **kwargs):
        """Validate that the personnel doesn't exceed 15 days per year"""
        if self.identifiant and self.date_debut and self.date_fin:
            # Validate date range
            if self.date_fin < self.date_debut:
                from django.core.exceptions import ValidationError
                raise ValidationError("La date de fin doit être après la date de début.")
            
            # Calculate days for this conge
            jours_ce_conge = self.nombre_jours()
            
            if jours_ce_conge <= 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Le nombre de jours de congé doit être supérieur à 0.")
            
            # Get the year of this conge
            year = self.date_debut.year
            
            # Calculate total days already used this year (excluding current conge if updating)
            total_days_used = self.get_total_days_per_year(year)
            
            # Check if adding this conge would exceed the limit
            if total_days_used + jours_ce_conge > 15:
                from django.core.exceptions import ValidationError
                jours_restants = 15 - total_days_used
                raise ValidationError(
                    f"Limite de congé dépassée. Ce personnel a déjà utilisé {total_days_used} jours "
                    f"sur 15 cette année ({year}). Il reste {jours_restants} jour(s) disponible(s)."
                )
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.identifiant.nom if self.identifiant else 'N/A'} - {self.date_debut}"

class DossierPersonnel(models.Model):
    id=models.AutoField(primary_key=True)
    namefile=models.CharField(max_length=100)
    identifiant=models.ForeignKey(Personnel,on_delete=models.CASCADE,null=True)
    file=models.FileField(upload_to='dossier/')
    def __str__(self):
        return self.namefile

class Jamat(models.Model):
    id=models.AutoField(primary_key=True)
    jamatid=models.CharField(max_length=100)
    nom=models.CharField(max_length=100)
    genrechoice=(('M','M'),('F','F'))
    genre=models.CharField(max_length=5,choices=genrechoice,default='M')
    telephone=models.CharField(null=True, blank=True, max_length=20)
    age=models.IntegerField()
    conversion_year=models.IntegerField(null=True, blank=True, verbose_name="Année de conversion")
    adress=models.CharField(max_length=100,null=True, blank=True)
    travail=models.CharField(max_length=100,null=True, blank=True)
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='images/')
    centre=models.CharField(max_length=100,choices=CENTRE_JAMAT_CHOICES,default='Antaniavo')
    email=models.CharField(max_length=50,null=True, blank=True)
    def __str__(self):
        return self.jamatid
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.imageprofile.url))
    
 
class ArchiveJamat(models.Model):
    id=models.AutoField(primary_key=True)
    archive_choice = (('Jamat', 'Jamat'), ('Autre', 'Autre'))
    archive_type=models.CharField(max_length=20, choices=archive_choice, default='Jamat', verbose_name="Type d'archive")
    jamat=models.ForeignKey(Jamat,on_delete=models.CASCADE,null=True,unique=False,verbose_name="Jamat")
    raison_choix = (('Renvoyé', 'Renvoyé'), ('Démission', 'Démission'), ('Décédé', 'Décédé'), ('Sortant', 'Sortant'), ('Autre', 'Autre'))
    raison=models.CharField(max_length=20, choices=raison_choix, default='Autre', verbose_name="Raison d'archive")
    archived_at=models.DateField(auto_now_add=True, verbose_name="Date d'archive")

    def __str__(self):
        return self.jamat.nom if self.jamat else "Archive Jamat"
    def nom(self):
        return self.jamat.nom if self.jamat else ""
    def image(self):
        if self.jamat and self.jamat.imageprofile and self.jamat.imageprofile.url:
            url = self.jamat.imageprofile.url
        else:
            url = '/media/images/avatar.jpg'
        return mark_safe('<img src="%s" width="50" height="50"/>' % url)
    def genre(self):
        return self.jamat.genre if self.jamat else ""
    def telephone(self):
        return self.jamat.telephone if self.jamat else ""
    def centre(self):
        return self.jamat.centre if self.jamat else ""
    def adresse(self):
        return self.jamat.adress if self.jamat else ""
    def travail(self):
        return self.jamat.travail if self.jamat else ""
    def age(self):
        return self.jamat.age if self.jamat else None
    def conversion_year(self):
        return self.jamat.conversion_year if self.jamat else None


class Madrassah(models.Model):
    madrassahid=models.CharField(max_length=100)
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='images/')
    nom=models.CharField(max_length=100)
    genrechoice=(('M','M'),('F','F'))
    genre=models.CharField(max_length=5,choices=genrechoice,default='M')
   
    age=models.CharField(max_length=20,null=True, blank=True)
    centrechoice=(('Antaniano','Antaniano'),('Ankaraobato','Ankaraobato'),
                  ('Manakara','Manakara'),("Andakana","Andakana"),("Abarambamby","Abarambamby"),
                     ('Andoarano','Andoarano'),("Ambolonaondry","Ambolonaondry"),("Limit-Est","Limit-Est"),
                        ('Limit-Ouest','Limit-Ouest'),("Analabe Manakara","Analabe Manakara")

                  )
    
    centre=models.CharField(max_length=20,choices=centrechoice,default='Antaniano',null=True, blank=True)
    adress=models.CharField(max_length=100,null=True, blank=True)
    class_madressah=models.CharField(max_length=100,null=True, blank=True)
    class_academic=models.CharField(max_length=100,null=True, blank=True)
    parent=models.CharField(max_length=100,null=True, blank=True)
    
    
    
    
    def __str__(self):
        return self.nom
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.imageprofile.url))


class ArchiveMadrassah(models.Model):
    id = models.AutoField(primary_key=True)
    archive_choice = (('Madrassah', 'Madrassah'), ('Autre', 'Autre'))
    archive_type = models.CharField(max_length=20, choices=archive_choice, default='Madrassah', verbose_name="Type d'archive")
    madrassah = models.ForeignKey(Madrassah, on_delete=models.CASCADE, null=True, verbose_name="Madrassah")
    raison_choix = (('Renvoyé', 'Renvoyé'), ('Démission', 'Démission'), ('Transfert', 'Transfert'), ('Autre', 'Autre'))
    raison = models.CharField(max_length=20, choices=raison_choix, default='Autre', verbose_name="Raison d'archive")
    archived_at = models.DateField(auto_now_add=True, verbose_name="Date d'archive")

    def __str__(self):
        return self.madrassah.nom if self.madrassah else "Archive Madrassah"


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
post_save.connect(create_user_profile,sender=User)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,null=True)
    avatar = models.ImageField(default='images/avatar.jpg', null=True,blank=True,upload_to='profile_images/')
    telephone=models.IntegerField(null=True, blank=True)
    email=models.CharField(max_length=50,null=True, blank=True)
    sectionchoice=(('multimedia','multimedia'),('cheick','cheick'),('administration','administration'),('rvs','rvs')
    )
    section=models.CharField(max_length=50,choices=sectionchoice,default='multimedia')
    centrechoice=(('Antaniano','Antaniano'),('Manakara','Manakara'))
    centre=models.CharField(max_length=20,choices=centrechoice,default='Antaniano')
    job=models.CharField(max_length=50,null=True, blank=True)


    def __str__(self):
        return self.user.username

class Pension(models.Model):
    id=models.AutoField(primary_key=True)
    nom=models.CharField(max_length=100)
    genrechoice=(('M','M'),('F','F'))
    genre=models.CharField(max_length=5,choices=genrechoice,default='M')
    telephone=models.CharField(null=True, blank=True, max_length=20)
    adress=models.CharField(max_length=100,null=True, blank=True)
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='images/')
    date_pension=models.DateField(null=True, blank=True)
    pension=models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True,verbose_name="Pension (Ar)")
    cause=models.CharField(max_length=100,null=True, blank=True,verbose_name="Cause")
    nombre_enfants=models.IntegerField(null=True, blank=True,verbose_name="Nombre d'enfants")
    age=models.IntegerField(null=True, blank=True,verbose_name="Age")
    def __str__(self):
        return self.nom
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.imageprofile.url))
   
    
class DossierPension(models.Model):
    id=models.AutoField(primary_key=True)
    namefile=models.CharField(max_length=100)
    file=models.FileField(upload_to='dossier/')
    pension=models.ForeignKey(Pension,on_delete=models.CASCADE,null=True)
    def __str__(self):
        return self.namefile



class Paiementpension(models.Model):
    id=models.AutoField(primary_key=True)
    pension=models.ForeignKey(Pension,on_delete=models.CASCADE,null=True)
    date_paiement=models.DateField(null=True, blank=True)
    montant=models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True,verbose_name="Montant (Ar)")
    statutchoice=(('Payé','Payé'),('Avance','Avance'))
    statut=models.CharField(max_length=100,choices=statutchoice,default='Payé')
    

    def __str__(self):
        return self.pension.nom
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.pension.imageprofile.url))
    def nom(self):
        return self.pension.nom
    def genre(self):
        return self.pension.genre
    def telephone(self):
        return self.pension.telephone
    def adress(self):
        return self.pension.adress

class Cimitiere(models.Model):
    id=models.AutoField(primary_key=True)
    nom=models.CharField(max_length=100,verbose_name="Nom complet")
    genrechoice=(('M','M'),('F','F'))
    genre=models.CharField(max_length=5,choices=genrechoice,default='M',verbose_name="Genre")
    imageprofile=models.ImageField(default='images/avatar.jpg',null=True,blank=True,upload_to='images/',verbose_name="Photo de profil")
    date_deces=models.DateField(null=True, blank=True,verbose_name="Date de décès")
    date_naissance=models.DateField(null=True, blank=True,verbose_name="Date de naissance")
    lieu_deces=models.CharField(max_length=100,null=True, blank=True,verbose_name="Lieu de décès")
    famille=models.CharField(max_length=100,null=True, blank=True,verbose_name="Famille")
    adress=models.CharField(max_length=100,null=True, blank=True,verbose_name="Adresse de la Famille")
    telephone=models.CharField(null=True, blank=True, max_length=20, verbose_name="Téléphone de la Famille")

    def __str__(self):
        return self.nom
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.imageprofile.url))
    def duree_enterement(self):
        date=datetime.now()
        year=date.year
        return year-self.date_deces.year
    def age(self):
        date=self.date_deces
        year=date.year
        return year-self.date_naissance.year
   
    
    
    
class DossierCimitiere(models.Model):
    id=models.AutoField(primary_key=True)
    namefile=models.CharField(max_length=100)
    file=models.FileField(upload_to='dossier_cimitiere/')
    cimitiere=models.ForeignKey(Cimitiere,on_delete=models.CASCADE,null=True)
    def __str__(self):
        return self.namefile
    
 

class Elite(models.Model):
    id=models.AutoField(primary_key=True)
    identifiant=models.ForeignKey(Etudiant,on_delete=models.CASCADE,related_name='elite',null=True,unique=False,verbose_name="Identifiant")
    def __str__(self):
        return self.identifiant.nom
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.identifiant.imageprofile.url))
    def nom(self):
        return self.identifiant.nom
    def genre(self):
        return self.identifiant.genre
    def telephone(self):
        return self.identifiant.telephone
    def ville(self):
        return self.identifiant.ville
    def centre(self):
        return self.identifiant.centre
    def designation(self):
        return self.identifiant.designation
    def Class(self):
        return self.identifiant.Class
    def institution(self):
        return self.identifiant.institution
    def fillier(self):
        return self.identifiant.fillier
    def date_naissance(self):
        return self.identifiant.date_naissance
    def date_entre(self):
        return self.identifiant.date_entre
     
class NoteElite(models.Model):
    id=models.AutoField(primary_key=True)
    notes=models.ForeignKey(NoteEtudiant,on_delete=models.CASCADE,null=True)
    def __str__(self):
        return self.notes.nom


class Universite(models.Model):
    id=models.AutoField(primary_key=True)
    universite=models.ForeignKey(Etudiant,on_delete=models.CASCADE,null=True,unique=False,verbose_name="Identifiant")
    email=models.EmailField(max_length=100,null=True, blank=True)
    def __str__(self):
        return self.universite.nom
    def Image(self):
        url = self.universite.imageprofile.url if self.universite.imageprofile and self.universite.imageprofile.url else '/media/images/avatar.jpg'
        return mark_safe('<img src="%s" width="50" height="50"/>'% (url))
    def nom(self):
        return self.universite.nom
    def genre(self):
        return self.universite.genre
    def telephone(self):
        return self.universite.telephone
    def ville(self):
        return self.universite.ville
    def centre(self):
        return self.universite.centre
    def designation(self):
        return self.universite.designation
    def Class(self):
        return self.universite.Class
    def institution(self):
        return self.universite.institution
    def ville(self):
        return self.universite.ville
    def fillier(self):
        return self.universite.fillier
    def date_naissance(self):
        return self.universite.date_naissance
    def date_entre(self):
        return self.universite.date_entre
    def date_sortie(self):
        return self.universite.date_sortie

# ... existing code ...

class Sortant(models.Model):
    """Model to track Sortant students (graduates/former students)"""
    id = models.AutoField(primary_key=True)
    sortant=models.ForeignKey(Etudiant,on_delete=models.CASCADE,null=True,unique=False,verbose_name="Identifiant")

    statut_matrimonial_choice = (('Célibataire', 'Célibataire'), ('Marié', 'Marié'), ('Divorcé', 'Divorcé'), ('Veuf', 'Veuf'))
    statut_matrimonial = models.CharField(max_length=100, choices=statut_matrimonial_choice, default='Célibataire', verbose_name="Statut matrimonial")
    # Academic History (optional - if they were a registered student)
 
    # Placement Information
    placement_choice = (
        ('Orphelinat', 'Orphelinat'),
        ('Université', 'Université'),
        ('Etudiant', 'Etudiant'),
        ('Autre', 'Autre')
    )
    placement_type = models.CharField(max_length=20, choices=placement_choice, default='Autre', verbose_name="Type de placement")
   
    # Current Job Information
    poste_actuel = models.CharField(max_length=100, null=True, blank=True, verbose_name="Poste actuel")
    entreprise = models.CharField(max_length=100, null=True, blank=True, verbose_name="Entreprise")
    lieu_travail = models.CharField(max_length=100, null=True, blank=True, verbose_name="Lieu de travail")
    date_embauche = models.DateField(null=True, blank=True, verbose_name="Date d'embauche")
    
    # Current Address
    adresse_actuelle = models.TextField(null=True, blank=True, verbose_name="Adresse actuelle")
     
    # Status
    status_choice = (
        ('Embauche', 'Embauche'),
        ('Non Embauche', 'Non Embauche')
    )
    status = models.CharField(max_length=20, choices=status_choice, default='Non Embauche')
    class Meta:
        verbose_name = "Sortant"
        verbose_name_plural = "Sortants"
    
    def __str__(self):
        return self.sortant.nom
    
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.sortant.imageprofile.url))
    def nom(self):
        return self.sortant.nom
    def genre(self):
        return self.sortant.genre
    def telephone(self):
        return self.sortant.telephone
    def ville(self):
        return self.sortant.ville
    def centre(self):
        return self.sortant.centre
    def designation(self):
        return self.sortant.designation
    def Class(self):
        return self.sortant.Class
    def institution(self):
        return self.sortant.institution
    def fillier(self):
        return self.sortant.fillier
   
    
    def duree_emploi(self):
        """Calculate duration of current employment in days"""
        if self.date_embauche:
            from datetime import date
            today = date.today()
            return (today - self.date_embauche).days
        return 0
    
    def est_orphelin(self):
        """Check if the person is an orphan by checking the Orphelin table"""
        if self.etudiant:
            # If they have a student record, check if they're in the Orphelin table
            return hasattr(self.etudiant, 'orphelin')
        return False
    
    def est_etudiant_enregistre(self):
        """Check if this person was a registered student"""
        return self.etudiant is not None

    
    def get_job_info(self):
        """Get formatted job information"""
        if self.poste_actuel and self.entreprise and self.lieu_travail:
            return f"{self.poste_actuel} chez {self.entreprise} à {self.lieu_travail}"
            return f"{self.poste_actuel} chez {self.entreprise}"
        elif self.poste_actuel:
            return self.poste_actuel
        elif self.entreprise:
            return f"Entreprise: {self.entreprise}"
        return "Aucun emploi renseigné"   

class Archive(models.Model):
    id=models.AutoField(primary_key=True)
    archive_choice = (('Orphelin', 'Orphelin'), ('Sortant', 'Sortant'), ('Université', 'Université'), ('crashcourses', 'crashcourses'),('Elite', 'Elite'),('Petit', 'Petit'),('Jeune', 'Jeune'),('Bachelor Dine', 'Bachelor Dine'),('Bachelor Université', 'Bachelor Université'),('internat', 'internat'),('dine', 'dine'),('Autre', 'Autre'))
    archive_type=models.CharField(max_length=20, choices=archive_choice, default='Autre', verbose_name="Type d'archive")
    archive=models.ForeignKey(Etudiant,on_delete=models.CASCADE,null=True,unique=False,verbose_name="Identifiant")
    raison_choix = (('Renvoyé', 'Renvoyé'), ('Démission', 'Démission'), ('Décédé', 'Décédé'), ('Sortant', 'Sortant'), ('Autre', 'Autre'))
    raison=models.CharField(max_length=20, choices=raison_choix, default='Autre', verbose_name="Raison d'archive")
    
    def __str__(self):
        return self.archive.nom
    def nom(self):
        return self.archive.nom
    def image(self):
        url = self.archive.imageprofile.url if self.archive.imageprofile and self.archive.imageprofile.url else '/media/images/avatar.jpg'
        return mark_safe('<img src="%s" width="50" height="50"/>' % url)
        
    def genre(self):
        return self.archive.genre
    def telephone(self):
        return self.archive.telephone
    def ville(self):
        return self.archive.ville
    def centre(self):
        return self.archive.centre
    def designation(self):
        return self.archive.designation
    def Class(self):
        return self.archive.Class

class International (models.Model):
    id=models.AutoField(primary_key=True)
    international=models.ForeignKey(Etudiant,on_delete=models.CASCADE,null=True,unique=False,verbose_name="Identifiant")
    pays_choice = (
        ('India', 'India'),
        ('Irak', 'Irak'),
        ('Iran', 'Iran'),
        ('Maroc', 'Maroc'),
        ('Indonésie', 'Indonésie'),
        ('France', 'France'),
        ('Autre', 'Autre')
    )
    pays=models.CharField(max_length=20, choices=pays_choice, default='Autre', verbose_name="Pays")
    date_depart=models.DateField(null=True, blank=True,verbose_name="Date de départ")
    duree_sejour=models.IntegerField(null=True, blank=True,verbose_name="Durée de séjour (année)")
  
    def __str__(self):
        return self.international.nom
    def Image(self):
        return mark_safe('<img src="%s" width="50" height="50"/>'% (self.international.imageprofile.url))
    def nom(self):
        return self.international.nom
    def genre(self):
        return self.international.genre
    def telephone(self):
        return self.international.telephone
    def ville(self):
        return self.international.ville
    def centre(self):
        return self.international.centre
    def designation(self):
        return self.international.designation
    def Class(self):
        return self.international.Class
    def institution(self):
        return self.international.institution
    def fillier(self):
        return self.international.fillier

