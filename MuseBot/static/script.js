function showSection(sectionId) {
    var sections = document.querySelectorAll('.section');
    sections.forEach(function(section) {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
}

// Show the first section by default (e.g., Chatbot section)
document.addEventListener("DOMContentLoaded", function() {
    showSection('chatbot');
});
