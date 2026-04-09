function openModalInfo(studentId) {
    const modal = document.getElementById('studentModal');
    const studentInfo = document.getElementById('studentInfo');
    const studentImage = document.getElementById('studentImage');
    const studentName = document.getElementById('studentName');

    // Fetch student data
    fetch(`/get_student_data/${studentId}/`)
        .then(response => response.json())
        .then(data => {
            studentImage.src = data.imageprofile;
            studentName.textContent = data.nom;

            const infoFields = [
                { label: 'Identifiant', value: data.identifiant },
                { label: 'Date de naissance', value: data.date_naissance },
                { label: 'Âge', value: data.Age },
                { label: 'Nom du père', value: data.nom_pere },
                { label: 'Nom de la mère', value: data.nom_mere },
                { label: 'Téléphone', value: data.telephone },
                { label: 'Téléphone parents', value: `${data.telephone_mere || ''} ${data.telephone_pere || ''}`.trim() },
                { label: 'Désignation', value: data.designation },
                { label: 'Institution', value: data.institution },
                { label: 'Ville', value: data.ville },
                { label: 'Filière', value: data.fillier },
                { label: 'Classe', value: data.Class },
                { label: 'Centre', value: data.centre },
                { label: 'Date d\'entrée', value: data.date_entre },
                { label: 'Date de sortie', value: data.date_sortie }
            ];

            studentInfo.innerHTML = infoFields.map(field => `
                <div class="py-2">
                    <span class="font-semibold">${field.label}:</span> 
                    <span>${field.value || '-'}</span>
                </div>
            `).join('');

            modal.classList.remove('hidden');
        });
}



