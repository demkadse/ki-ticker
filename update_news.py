# ... (Vorheriger Python Code bleibt gleich bis zum Script-Teil am Ende) ...
    <script>
        function checkResults() {
            const cards = document.querySelectorAll('.card');
            let visible = 0;
            cards.forEach(c => { if(c.style.display !== 'none') visible++; });
            // Das JS schaltet die Meldung nur ein, wenn wirklich 0 Karten da sind
            document.getElementById('noResults').style.display = visible === 0 ? 'block' : 'none';
        }
        function filterCat(cat, btn) {
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('searchInput').value = '';
            document.querySelectorAll('.card').forEach(el => {
                el.style.display = (cat === 'all' || el.getAttribute('data-source') === cat) ? 'flex' : 'none';
            });
            checkResults(); // Prüfung nach Kategorie-Wechsel
        }
        function filterNews(t){
            const v = t.toLowerCase();
            document.getElementById('clearSearch').style.display = v ? 'block' : 'none';
            document.querySelectorAll('.card').forEach(el => {
                el.style.display = el.getAttribute('data-content').includes(v) ? 'flex' : 'none';
            });
            checkResults(); // Prüfung nach Sucheingabe
        }
        function applySearch(word) {
            document.getElementById('searchInput').value = word;
            filterNews(word);
        }
        function clearSearch() {
            document.getElementById('searchInput').value = '';
            filterNews('');
        }
        document.getElementById('searchInput').oninput=(e)=>filterNews(e.target.value);
        function copyToClipboard(t){navigator.clipboard.writeText(t).then(()=>alert('Kopiert!'));}
    </script>
