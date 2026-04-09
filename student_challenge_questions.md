# Liste de Questions pour Challenger le Code et l'IA (craStudentManagement)

Ce document contient une série de questions et de scénarios de test pour évaluer la robustesse du système de gestion des étudiants, ainsi que la capacité de l'IA à analyser et manipuler les données du projet.

## 1. Questions de Base (Niveau Simple)
*Ces questions testent la compréhension directe des modèles et des relations simples.*

- **Q1 :** Combien y a-t-il d'étudiants actuellement enregistrés avec le statut "Actif" ?
- **Q2 :** Quelle est la liste des centres disponibles dans le système (en incluant les alias) ?
- **Q3 :** Quel est le nombre total de filles (Genre 'F') parmi les étudiants ?
- **Q4 :** Lister les 5 derniers étudiants ajoutés au système par leur date d'entrée.
- **Q5 :** vrb123 ?

## 2. Questions de Statistiques et Répartitions (Niveau Moyen)
*Ces questions nécessitent des agrégations et des calculs sur plusieurs enregistrements.*

- **Q6 :** Quelle est la répartition des étudiants par centre ? (Nombre d'étudiants par centre principal).
- **Q7 :** Quel est l'âge moyen des étudiants actuellement actifs ?
- **Q8 :** Quel est le pourcentage d'orphelins par rapport au nombre total d'étudiants ?
- **Q9 :** Quelle est la répartition des étudiants par classe (de la PS à la 6ème année d'université) ?
- **Q10 :** Quel est le centre qui compte le plus grand nombre d'étudiants de type "Elite" ?

## 3. Questions Complexes et Analyse de Données (Niveau Avancé)
*Ces questions impliquent des jointures, des filtres complexes ou des calculs de durée.*

- **Q11 :** Identifier les étudiants qui ont plus de 3 absences enregistrées dans la table `Presence`.
- **Q12 :** Calculer la moyenne générale des notes (S1, S2, S3) pour chaque centre. Quel centre a la meilleure performance académique ?
- **Q13 :** Lister les étudiants "Sortants" qui ont trouvé un emploi (status 'Embauche') et calculer la durée moyenne entre leur date de sortie et leur date d'embauche.
- **Q14 :** Quels sont les étudiants qui ont reçu un avertissement (`Avertissement`) et qui ont également une moyenne académique inférieure à 10 ?
- **Q15 :** Pour le personnel (`Personnel`), calculer le nombre total de jours de congé restants pour l'année en cours, groupé par section (Administration, Cuisine, etc.).

## 4. Challenges pour l'IA (Logique et Code)
*Ces défis testent la capacité de l'IA à proposer des modifications ou des optimisations.*

- **C1 :** Comment modifierais-tu le modèle `Etudiant` pour ajouter un système de tutorat entre un étudiant "Elite" et un étudiant "Jeune" ?
- **C2 :** Écris une requête Django ORM complexe pour trouver tous les étudiants qui n'ont jamais manqué la prière du 'Fajr' durant le dernier mois.
- **C3 :** Propose une optimisation pour la méthode `get_centre_choices` afin d'éviter les imports circulaires de manière plus élégante.
- **C4 :** Si on devait ajouter un module de "Suivi de Santé", quels nouveaux modèles et relations proposerais-tu d'ajouter à `main/models.py` ?
- **C5 :** Comment implémenterait-on une règle de gestion qui empêche un étudiant d'être marqué "Présent" s'il a une date de sortie déjà passée ?

## 5. Scénarios de Test (Robustesse)
- **S1 :** Que se passe-t-il si on essaie d'ajouter un congé de 20 jours à un membre du personnel ? (Vérification de la validation des 15 jours).
- **S2 :** Si un centre est supprimé, qu'advient-il des étudiants qui y sont rattachés ? (Analyse de la stratégie de suppression).
- **S3 :** Tester l'unicité de l'identifiant étudiant : que se passe-t-il en cas de doublon lors d'un import massif ?

