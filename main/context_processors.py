# myapp/context_processors.py

def menu_context(request):
    role = "admin"  # Assuming the role is attached to the user model
    static_image_path = '/static/image/'  # Base path for images
    '''
     {"icon": f"{static_image_path}assignment.png", "label": "Assignments", "href": "/list/assignments", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}result.png", "label": "Results", "href": "/list/results", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}attendance.png", "label": "Attendance", "href": "/list/attendance", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}calendar.png", "label": "Events", "href": "/list/events", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}message.png", "label": "Messages", "href": "/list/messages", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}announcement.png", "label": "Announcements", "href": "/list/announcements", "visible": ["admin", "teacher", "student", "parent"]},
    '''
    menuItems = [
        {
            "title": "MENU",
            "items": [
                {"icon": f"{static_image_path}home.png", "label": "Acceuil", "href": "/", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}message.png", "label": "Chatbot IA", "href": "/api/chatbot/", "visible": ["admin", "teacher", "student", "parent"]},
                {
                    "icon": f"{static_image_path}teacher.png", 
                    "label": "Etudiants", 
                    "href": "#", 
                    "visible": ["admin", "teacher"],
                    "hasSubmenu": True,
                    "submenu": [
                        {"icon": f"{static_image_path}home.png", "label": "Tableau de bord", "href": "/etudiants/dashboard/", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}teacher.png", "label": "List Etudiants", "href": "/student", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}subject.png", "label": "Notes", "href": "/notes", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}class.png", "label": "Archive Etudiants", "href": "/student/archived/", "visible": ["admin", "teacher"]},
                    ]
                },
                {
                    "icon": f"{static_image_path}student.png", 
                    "label": "Orphelin", 
                    "href": "#", 
                    "visible": ["admin", "teacher"],
                    "hasSubmenu": True,
                    "submenu": [
                        {"icon": f"{static_image_path}home.png", "label": "Tableau de bord", "href": "/orphelin/dashboard/", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}teacher.png", "label": "List Orphelins", "href": "/orphelin", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}subject.png", "label": "Notes", "href": "/noteorphelin", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}class.png", "label": "Archive des Orphelin", "href": "/orphelin/archive/", "visible": ["admin", "teacher"]},
                    ]
                },
                {
                    "icon": f"{static_image_path}class.png", 
                    "label": "Université", 
                    "href": "#", 
                    "visible": ["admin", "teacher"],
                    "hasSubmenu": True,
                    "submenu": [
                        {"icon": f"{static_image_path}home.png", "label": "Tableau de bord", "href": "/universite/dashboard/", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}class.png", "label": "List Universités", "href": "/universite", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}subject.png", "label": "Notes Universités", "href": "/notesuniversite", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}exam.png", "label": "International", "href": "/universite/international/", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}class.png", "label": "Archive Universités", "href": "/universite/archive/", "visible": ["admin", "teacher"]},
                    ]
                },
                {"icon": f"{static_image_path}student.png", "label": "Sortant", "href": "/sortant", "visible": ["admin", "teacher"]},

                {
                    "icon": f"{static_image_path}exam.png",
                    "label": "Elites",
                    "href": "#",
                    "visible": ["admin", "teacher", "student", "parent"],
                    "hasSubmenu": True,
                    "submenu": [
                        {"icon": f"{static_image_path}home.png", "label": "Tableau de bord", "href": "/elite/dashboard/", "visible": ["admin", "teacher", "student", "parent"]},
                        {"icon": f"{static_image_path}teacher.png", "label": "List Elites", "href": "/elite", "visible": ["admin", "teacher", "student", "parent"]},
                        {"icon": f"{static_image_path}subject.png", "label": "Notes Elites", "href": "/noteelite", "visible": ["admin", "teacher", "student", "parent"]},
                        {"icon": f"{static_image_path}class.png", "label": "Archive Elites", "href": "/elite/archive/", "visible": ["admin", "teacher"]},
                    ]
                },

                {
                    "icon": f"{static_image_path}parent.png",
                    "label": "Personnels",
                    "href": "#",
                    "visible": ["admin"],
                    "hasSubmenu": True,
                    "submenu": [
                        {"icon": f"{static_image_path}teacher.png", "label": "Liste Personnel", "href": "/personnel", "visible": ["admin"]},
                        {"icon": f"{static_image_path}calendar.png", "label": "Gestion Congés", "href": "/personnel/conge/gestion", "visible": ["admin"]},
                    ]
                },
                {
                    "icon": f"{static_image_path}class.png",
                    "label": "Jamat",
                    "href": "#",
                    "visible": ["admin", "teacher"],
                    "hasSubmenu": True,
                    "submenu": [
                        {"icon": f"{static_image_path}home.png", "label": "Tableau de bord", "href": "/jamat/dashboard/", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}teacher.png", "label": "List Jamats", "href": "/jamat", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}class.png", "label": "Archive Jamats", "href": "/jamat/archive/", "visible": ["admin", "teacher"]},
                    ]
                },
                {
                    "icon": f"{static_image_path}lesson.png",
                    "label": "Madrassah",
                    "href": "#",
                    "visible": ["admin", "teacher"],
                    "hasSubmenu": True,
                    "submenu": [
                        {"icon": f"{static_image_path}home.png", "label": "Tableau de bord", "href": "/madrassah/dashboard/", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}teacher.png", "label": "Liste de Madrassah", "href": "/madrassah/", "visible": ["admin", "teacher"]},
                        {"icon": f"{static_image_path}class.png", "label": "Archive Madrassah", "href": "/madrassah/archive/", "visible": ["admin", "teacher"]},
                    ],
                },
                {"icon": f"{static_image_path}exam.png", "label": "Pension", "href": "/pension", "visible": ["admin", "teacher", "student", "parent"]},
              
                {"icon": f"{static_image_path}class.png", "label": "Cimitiere", "href": "/cimitiere", "visible": ["admin", "teacher", "student", "parent"]},
              #  {"icon": f"{static_image_path}exam.png", "label": "Avertissements", "href": "/avertissement", "visible": ["admin", "teacher", "student", "parent"]},

               
            ],
        },
        {
            "title": "Autre",
            "items": [
                {"icon": f"{static_image_path}profile.png", "label": "Profile", "href": "/profile", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}setting.png", "label": "Settings", "href": "/settings", "visible": ["admin", "teacher", "student", "parent"]},
                {"icon": f"{static_image_path}logout.png", "label": "Logout", "href": "/logout", "visible": ["admin", "teacher", "student", "parent"]},
            ],
        },
    ]
    return {'menuItems': menuItems, 'role': role}
