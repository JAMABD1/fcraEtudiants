from django.urls import path
from main import views
 
urlpatterns = [
    path('',views.loginSingup,name="loginSingup"),
    path('singin/',views.singin,name="singin"),
path('logout/',views.logoutUser,name='logout'),
   
     path('dashboard/',views.home,name="home"),
     path('orphelin/dashboard/',views.orphelin_dashboard,name="orphelin_dashboard"),
     path('jamat/dashboard/',views.jamat_dashboard,name="jamat_dashboard"),
     path('elite/dashboard/',views.elite_dashboard,name="elite_dashboard"),
     path('etudiants/dashboard/',views.etudiants_dashboard,name="etudiants_dashboard"),
     path('student/',views.student,name="student"),
     path('student/archived/',views.archived_students,name="archived_students"),
     path('orphelin/archive/',views.archived_orphelins,name="archived_orphelins"),
     path('jamat/archive/',views.archived_jamats,name="archived_jamats"),
     path('madrassah/dashboard/',views.madrassah_dashboard,name="madrassah_dashboard"),
     path('madrassah/archive/',views.archived_madrassahs,name="archived_madrassahs"),
     path('elite/archive/',views.archived_elites,name="archived_elites"),
     path('universite/',views.universite,name="universite"),
     path('universite/dashboard/',views.universite_dashboard,name="universite_dashboard"),
     path('notesuniversite/',views.notesuniversite,name="notesuniversite"),
     path('universite/archive/',views.archived_universites,name="archived_universites"),
     path('universite/international/',views.international,name="international"),
     path('sortant/',views.sortant,name="sortant"),
     path('sortant/view/<int:sortant_id>/',views.viewSortant,name="viewSortant"),
     
      path('student/<int:id>',views.studentdelete,name="studentdelete"),
       path('student/search',views.studentSearch,name="studentSearch"),
       path('student/groupby',views.studentGroupby,name="studentGroupby"),

     path('student/edit',views.studentUpdate,name="studentUpdate"),
          path('student/upload',views.studentUpload,name="studentUpload"),
          path('student/view',views.studentView,name="studentView"),
          path('student/view/<str:etudiantid>',views.viewStudent,name="viewStudentByIdentifiant"),
      path('students/<str:etudiantid>',views.viewStudentMinimal,name="viewStudentMinimal"),
           path('notes/search',views.noteSearch,name="noteSearch"),
           path('notes/filter',views.noteFilter,name="noteFilter"),
      


     path('student/filter',views.studentFilter,name="studentFilter"),
        path('personnel/filter',views.PersonnelFilter,name="PersonnelFilter"),

     

     path('notes/',views.notes,name="notes"),
     path('noteorphelin/',views.noteorphelin,name="noteorphelin"),
     path('notes/edit',views.notesUpdate,name="notesUpdate"),
      path('notes/<int:id>',views.notesdelete,name="notesdelete"),
       path('notes/GetId',views.notesGetId,name="notesGetId"),
          path('notes/showstat',views.notes,name="notesshowstat"),

     path('avertissement/',views.avertissement,name="avertissement"),
     path('avertissement/GetId',views.avertissementGetId,name="avertissementGetId"),
      path('avertissement/edit',views.avertissementUpdate,name="avertissementUpdate"),
       path('avertissement/<int:id>',views.avertissementdelete,name="avertissementdelete"),

      





     path('presence/',views.presence,name="presence"),
     path('presence/GetId',views.presenceGetId,name="presenceGetId"),



   #   path('viewStudent/<str:etudiantid>',views.viewStudent,name="viewStudent"),

      path('personnel/',views.personnel,name="personnel"),
      path('personnel/search',views.personnelSearch,name="personnelSearch"),
        path('personnel/<int:id>',views.personneldelete,name="personneldelete"),
      path('personnel/edit',views.personnelUpdate,name="personnelUpdate"),

       path('viewpersonnel/<int:id>',views.viewPersonnel,name="viewPersonnel"),
       path('personnel/conge/gestion',views.gestion_conge,name="gestion_conge"),




    path('jamat/',views.jamat,name="jamat"),
     
        path('viewjamat/<int:id>',views.viewJamat,name="viewJamat"),


      path('madrassah/',views.madrassah,name="madrassah"),
    
      path('viewmadrassah/<str:id>',views.viewMadrassah,name="viewMadrassah"),
path('viewdocument/<int:id>',views.viewdocument,name="viewdocument"),


path('viewuser/',views.viewUser,name="viewuser"),



path("dashboard/Getpass",views.getPassStat,name="getPassStat"),
path("dashboard/Getbatch",views.getGetbatch,name="getGetbatch"),

path("dashboard/Getfillier",views.getGetfillier,name="getGetfillier"),
 
path('orphelin/',views.orphelin,name="orphelin"),
path('orphelin/edit',views.orphelinEdit,name="orphelinEdit"),
path('orphelin/search',views.orphelinSearch,name="orphelinSearch"),
     path('orphelin/groupby',views.orphelinGroupby,name="orphelinGroupby"),
     path('orphelin/filter',views.orphelinfilter,name="orphelinfilter"),

path('elite/',views.elite,name="elite"),
path('noteelite/',views.noteelite,name="noteelite"),

path('cimitiere/',views.cimitiere,name="cimitiere"),
path('cimitiere/edit',views.cimitiereEdit,name="cimitiereEdit"),
path('cimitiere/search',views.cimitiereSearch,name="cimitiereSearch"),
     path('cimitiere/filter',views.cimitiereFilter,name="cimitiereFilter"),
     path('cimitiere/<int:id>',views.cimitiereDelete,name="cimitiereDelete"),
     path('cimitiere/view/<int:id>',views.viewCimitiere,name="viewCimitiere"),
     path('get_cimitiere_data/<int:cimitiere_id>/', views.get_cimitiere_data, name='get_cimitiere_data'),

     path('api/chart-data/', views.chart_data, name='chart_data'),
      path('api/gender-distribution/', views.gender_distribution, name='gender_distribution'),
          path('api/designation-distribution/', views.designation_distribution, name='designation_distribution'),
            path('api/enrolled-institution-distribution/', views.enrolled_by_institution_distribution, name='enrolled_by_institution_distribution'),
                path('get_student_data/<int:student_id>/', views.get_student_data, name='get_student_data'),


 path('pension/',views.pension,name="pension"),
 path('pension/edit',views.pensionEdit,name="pensionEdit"),
 path('pension/search',views.pensionSearch,name="pensionSearch"),
 path('pension/filter',views.pensionFilter,name="pensionFilter"),

 path('pension/view/<int:id>',views.viewPension,name="viewPension"),
 
]
