"""Interface text in English, Spanish, French and Haitian Kreyòl.

Keys are the English strings. Anything not listed falls back to English.
French and Kreyòl were drafted with AI assistance and need review by
native speakers before field use (noted on the Data & method page).
"""

LANGS = {"en": "English", "es": "Español", "fr": "Français", "ht": "Kreyòl"}

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "fr": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"],
    "ht": ["Jan", "Fev", "Mas", "Avr", "Me", "Jen", "Jiy", "Out", "Sep", "Okt", "Nov", "Des"],
}

T = {
    # navigation
    "Plan my season": {"es": "Mi temporada", "fr": "Ma saison", "ht": "Sezon mwen"},
    "Water watch": {"es": "Agua", "fr": "Eau", "ht": "Dlo"},
    "Storm ready": {"es": "Listo para tormentas", "fr": "Prêt pour la tempête", "ht": "Pare pou tanpèt"},
    "After a storm": {"es": "Después de la tormenta", "fr": "Après la tempête", "ht": "Apre tanpèt la"},
    "Ask FarmFit": {"es": "Pregunta a FarmFit", "fr": "Demander à FarmFit", "ht": "Mande FarmFit"},
    "Data & method": {"es": "Datos y método", "fr": "Données et méthode", "ht": "Done ak metòd"},
    # masthead
    "A farmer's almanac, redrawn with satellite data: what to plant, when to water, and how to get through the storm season with your soil and your harvest intact.": {
        "es": "Un almanaque del agricultor, redibujado con datos satelitales: qué sembrar, cuándo regar y cómo pasar la temporada de tormentas con el suelo y la cosecha a salvo.",
        "fr": "Un almanach du paysan, redessiné avec des données satellites : quoi planter, quand arroser et comment traverser la saison des tempêtes en gardant sol et récolte.",
        "ht": "Yon almanak pou kiltivatè, ki fèt ak done satelit: kisa pou plante, kilè pou wouze, ak kijan pou pase sezon tanpèt la san pèdi tè a ak rekòt la."},
    "My own farm (pick on the map)": {"es": "Mi finca (elegir en el mapa)", "fr": "Ma ferme (choisir sur la carte)", "ht": "Pwòp jaden mwen (chwazi sou kat la)"},
    # section intros
    "Tell us what you grow now. We search every 12-month rotation of up to four crops and show the three that best protect your harvest, your soil and your water, next to your own.": {
        "es": "Díganos qué siembra ahora. Revisamos todas las rotaciones de 12 meses de hasta cuatro cultivos y mostramos las tres que mejor protegen su cosecha, su suelo y su agua, junto a la suya.",
        "fr": "Dites-nous ce que vous cultivez. Nous examinons toutes les rotations de 12 mois jusqu'à quatre cultures et montrons les trois qui protègent le mieux votre récolte, votre sol et votre eau, à côté de la vôtre.",
        "ht": "Di nou kisa w ap plante kounye a. Nou chèche tout wotasyon 12 mwa ak jiska kat rekòt, epi nou montre twa ki pi byen pwoteje rekòt ou, tè ou ak dlo ou, bò kote pa w la."},
    "Is the farm drier or wetter than normal right now? Recent NASA rain and soil moisture are ranked against the same weeks in each of the last 30 years, then turned into this week's watering advice.": {
        "es": "¿Está la finca más seca o más húmeda de lo normal? La lluvia y la humedad del suelo recientes de la NASA se comparan con las mismas semanas de los últimos 30 años y se convierten en consejos de riego para esta semana.",
        "fr": "La ferme est-elle plus sèche ou plus humide que d'habitude ? La pluie et l'humidité du sol récentes de la NASA sont comparées aux mêmes semaines des 30 dernières années, puis traduites en conseils d'arrosage.",
        "ht": "Èske jaden an pi sèk oswa pi mouye pase nòmal? Nou konpare lapli ak imidite tè NASA dènye semèn yo ak menm semèn yo nan 30 dènye ane yo, epi nou ba w konsèy pou wouze semèn sa a."},
    "Hurricanes can't be stopped, but a farm can be ready: the right crops in the ground in the risky months, and a short checklist when a storm is on the way.": {
        "es": "Los huracanes no se pueden detener, pero una finca puede estar lista: los cultivos correctos en los meses de riesgo y una lista corta cuando viene una tormenta.",
        "fr": "On ne peut pas arrêter un ouragan, mais une ferme peut être prête : les bonnes cultures pendant les mois à risque, et une courte liste quand une tempête approche.",
        "ht": "Nou pa ka kanpe siklòn, men yon jaden ka pare: bon rekòt nan tè a pandan mwa ki gen risk yo, ak yon ti lis pou fè lè yon tanpèt ap vini."},
    "Photograph the field. AI describes what it can see, NASA rain and soil moisture add context, and clear food-safety rules set a staged path back to harvest.": {
        "es": "Fotografíe el campo. La IA describe lo que ve, la lluvia y humedad del suelo de la NASA dan contexto y reglas claras de inocuidad marcan el camino de vuelta a la cosecha.",
        "fr": "Photographiez la parcelle. L'IA décrit ce qu'elle voit, la pluie et l'humidité du sol de la NASA donnent le contexte, et des règles claires de sécurité alimentaire tracent le retour à la récolte.",
        "ht": "Pran yon foto jaden an. IA dekri sa li wè, done lapli ak imidite NASA bay kontèks, epi règ sekirite manje yo montre chemen pou retounen nan rekòt."},
    "Ask anything about your farm, in your language. Answers draw on this farm's NASA climate record, storm history, rotations and water status.": {
        "es": "Pregunte lo que quiera sobre su finca, en su idioma. Las respuestas usan el clima NASA de esta finca, su historial de tormentas, rotaciones y estado del agua.",
        "fr": "Posez toute question sur votre ferme, dans votre langue. Les réponses s'appuient sur le climat NASA de cette ferme, son historique de tempêtes, ses rotations et l'état de l'eau.",
        "ht": "Poze nenpòt kesyon sou jaden ou, nan lang ou. Repons yo baze sou done klima NASA jaden sa a, istwa tanpèt li, wotasyon ak eta dlo a."},
    "Every number in FarmFit traces back to an open dataset and a published method. Here is the full list, how each one reaches the app, and where human judgment still matters.": {
        "es": "Cada número en FarmFit proviene de un conjunto de datos abierto y un método publicado. Aquí está la lista completa y dónde sigue importando el juicio humano.",
        "fr": "Chaque chiffre de FarmFit provient d'un jeu de données ouvert et d'une méthode publiée. Voici la liste complète et les limites où le jugement humain compte.",
        "ht": "Chak chif nan FarmFit soti nan yon done louvri ak yon metòd ki pibliye. Men tout lis la, ak kote jijman moun toujou enpòtan."},
    # headings
    "What you grow now": {"es": "Lo que siembra ahora", "fr": "Ce que vous cultivez", "ht": "Sa w ap plante kounye a"},
    "What matters most": {"es": "Lo más importante", "fr": "Votre priorité", "ht": "Sa ki pi enpòtan"},
    "Survive storms": {"es": "Resistir tormentas", "fr": "Résister aux tempêtes", "ht": "Kenbe fèm nan tanpèt"},
    "Rebuild my soil": {"es": "Recuperar mi suelo", "fr": "Reconstruire mon sol", "ht": "Rebati tè mwen"},
    "Save water": {"es": "Ahorrar agua", "fr": "Économiser l'eau", "ht": "Ekonomize dlo"},
    "Water for irrigation": {"es": "Agua para riego", "fr": "Eau d'irrigation", "ht": "Dlo pou wouze"},
    "More options": {"es": "Más opciones", "fr": "Plus d'options", "ht": "Plis opsyon"},
    "Your year, four ways": {"es": "Su año, de cuatro maneras", "fr": "Votre année, de quatre façons", "ht": "Ane ou, kat fason"},
    "rotations compared": {"es": "rotaciones comparadas", "fr": "rotations comparées", "ht": "wotasyon konpare"},
    "Take the plan with you": {"es": "Llévese el plan", "fr": "Emportez le plan", "ht": "Pran plan an avè w"},
    "Download (works offline)": {"es": "Descargar (sin internet)", "fr": "Télécharger (hors ligne)", "ht": "Telechaje (san entènèt)"},
    "Share on WhatsApp": {"es": "Compartir por WhatsApp", "fr": "Partager sur WhatsApp", "ht": "Pataje sou WhatsApp"},
    "Printable almanac (A4)": {"es": "Almanaque para imprimir (A4)", "fr": "Almanach à imprimer (A4)", "ht": "Almanak pou enprime (A4)"},
    "Get storm and drought alerts on your phone": {"es": "Reciba alertas de tormenta y sequía en su teléfono", "fr": "Recevez les alertes tempête et sécheresse sur votre téléphone", "ht": "Resevwa alèt tanpèt ak sechrès sou telefòn ou"},
    "This week": {"es": "Esta semana", "fr": "Cette semaine", "ht": "Semèn sa a"},
    "Storm watch, live from NOAA's National Hurricane Center": {"es": "Vigilancia de tormentas, en vivo del Centro Nacional de Huracanes (NOAA)", "fr": "Veille cyclonique en direct du National Hurricane Center (NOAA)", "ht": "Siveyans tanpèt, an dirèk nan Sant Nasyonal Siklòn NOAA"},
    "Do these now": {"es": "Haga esto ahora", "fr": "À faire maintenant", "ht": "Fè sa yo kounye a"},
    "When a storm is forecast: your checklist for {month}": {"es": "Cuando se pronostica una tormenta: su lista para {month}", "fr": "Quand une tempête est annoncée : votre liste pour {month}", "ht": "Lè yo anonse yon tanpèt: lis ou pou {month}"},
    "in the field": {"es": "en el campo", "fr": "dans le champ", "ht": "nan jaden an"},
    "How exposed is this farm?": {"es": "¿Qué tan expuesta está esta finca?", "fr": "Quelle est l'exposition de cette ferme ?", "ht": "Ki jan jaden sa a ekspoze?"},
    "Stress-test your calendar": {"es": "Ponga a prueba su calendario", "fr": "Testez votre calendrier", "ht": "Teste kalandriye ou"},
    "Your path back": {"es": "Su camino de regreso", "fr": "Votre chemin de retour", "ht": "Chemen pou retounen"},
    "Ground truth: your own soil sensor": {"es": "Verdad de campo: su propio sensor de suelo", "fr": "Vérité terrain : votre capteur de sol", "ht": "Verite sou teren: pwòp detektè tè ou"},
    # plans
    "Your current rotation": {"es": "Su rotación actual", "fr": "Votre rotation actuelle", "ht": "Wotasyon ou kounye a"},
    "Storm-smart": {"es": "Inteligente ante tormentas", "fr": "Anti-tempête", "ht": "Entelijan pou tanpèt"},
    "Soil builder": {"es": "Constructor de suelo", "fr": "Bâtisseur de sol", "ht": "Bati tè"},
    "Water saver": {"es": "Ahorro de agua", "fr": "Économe en eau", "ht": "Ekonomi dlo"},
    "What you plant now": {"es": "Lo que siembra ahora", "fr": "Ce que vous plantez", "ht": "Sa w plante kounye a"},
    "Best for your priority": {"es": "Mejor para su prioridad", "fr": "Meilleur pour votre priorité", "ht": "Pi bon pou priyorite ou"},
    "Alternative": {"es": "Alternativa", "fr": "Alternative", "ht": "Lòt chwa"},
    "Storm & flood safety": {"es": "Seguridad ante tormentas e inundaciones", "fr": "Sécurité tempêtes et inondations", "ht": "Sekirite tanpèt ak inondasyon"},
    "Soil health": {"es": "Salud del suelo", "fr": "Santé du sol", "ht": "Sante tè"},
    "Water saving": {"es": "Ahorro de agua", "fr": "Économie d'eau", "ht": "Ekonomi dlo"},
    "Climate fit": {"es": "Ajuste al clima", "fr": "Adapté au climat", "ht": "Bon pou klima a"},
    "Food & income": {"es": "Comida e ingresos", "fr": "Nourriture et revenu", "ht": "Manje ak lajan"},
    "Harvest lost to storms and floods, average year": {"es": "Cosecha perdida por tormentas e inundaciones, año promedio", "fr": "Récolte perdue (tempêtes, inondations), année moyenne", "ht": "Rekòt ki pèdi nan tanpèt ak inondasyon, ane mwayèn"},
    "Bare months": {"es": "Meses sin cobertura", "fr": "Mois de sol nu", "ht": "Mwa tè a toutouni"},
    "legume months": {"es": "meses de leguminosas", "fr": "mois de légumineuses", "ht": "mwa pwa"},
    "Irrigation": {"es": "Riego", "fr": "Irrigation", "ht": "Irigasyon"},
    "a year": {"es": "al año", "fr": "par an", "ht": "pa ane"},
    "Why · evidence · gaps": {"es": "Por qué · evidencia · vacíos", "fr": "Pourquoi · preuves · lacunes", "ht": "Poukisa · prèv · sa ki manke"},
    # water stamps / verdicts
    "Very dry": {"es": "Muy seco", "fr": "Très sec", "ht": "Trè sèk"},
    "Drier than usual": {"es": "Más seco de lo normal", "fr": "Plus sec que d'habitude", "ht": "Pi sèk pase nòmal"},
    "Near normal": {"es": "Cerca de lo normal", "fr": "Proche de la normale", "ht": "Prèske nòmal"},
    "Wetter than usual": {"es": "Más húmedo de lo normal", "fr": "Plus humide que d'habitude", "ht": "Pi mouye pase nòmal"},
    "Very wet": {"es": "Muy húmedo", "fr": "Très humide", "ht": "Trè mouye"},
    "No watering needed": {"es": "No hace falta regar", "fr": "Pas besoin d'arroser", "ht": "Pa bezwen wouze"},
    "Water about {mm} mm this week": {"es": "Riegue unos {mm} mm esta semana", "fr": "Arrosez environ {mm} mm cette semaine", "ht": "Wouze anviwon {mm} mm semèn sa a"},
    "Nothing planted this month": {"es": "Nada sembrado este mes", "fr": "Rien de planté ce mois-ci", "ht": "Anyen pa plante mwa sa a"},
    # storm stamps
    "act now": {"es": "actúe ya", "fr": "agir maintenant", "ht": "aji kounye a"},
    "get ready": {"es": "prepárese", "fr": "préparez-vous", "ht": "pare w"},
    "monitor": {"es": "vigilar", "fr": "surveiller", "ht": "veye"},
    "all clear": {"es": "sin peligro", "fr": "rien à signaler", "ht": "pa gen danje"},
    "No active tropical storms in the Atlantic right now.": {"es": "No hay tormentas tropicales activas en el Atlántico ahora.", "fr": "Aucune tempête tropicale active dans l'Atlantique en ce moment.", "ht": "Pa gen okenn tanpèt twopikal aktif nan Atlantik kounye a."},
    # checklist templates
    "Harvest what you can sell now: {crop} is at the {stage} stage, so an early harvest beats a total loss.": {
        "es": "Coseche lo que pueda vender ya: {crop} está en etapa {stage}; cosechar antes es mejor que perderlo todo.",
        "fr": "Récoltez ce qui se vend dès maintenant : {crop} est au stade {stage}, mieux vaut récolter tôt que tout perdre.",
        "ht": "Rekòlte sa ou ka vann kounye a: {crop} nan etap {stage}, li pi bon pou rekòlte bonè pase pou pèdi tout."},
    "{crop} is tall and top-heavy: prop or stake plants, and for plantain harvest mature bunches first.": {
        "es": "{crop} es alto y pesado arriba: apuntale las plantas y, en plátano, coseche primero los racimos maduros.",
        "fr": "{crop} est haut et lourd : tuteurez les plants et, pour la banane plantain, récoltez d'abord les régimes mûrs.",
        "ht": "{crop} wo epi lou anlè: mete poto pou kenbe plant yo, epi pou bannann rekòlte rejim ki mi yo an premye."},
    "Check stakes and trellis lines on the {crop}; loosen ties so stems bend rather than snap.": {
        "es": "Revise tutores y espalderas de {crop}; afloje las amarras para que los tallos se doblen y no se rompan.",
        "fr": "Vérifiez tuteurs et palissages de {crop} ; desserrez les liens pour que les tiges plient sans casser.",
        "ht": "Tcheke poto ak fil {crop} yo; lage mare yo pou branch yo ka pliye olye yo kase."},
    "{crop} is mostly underground and usually survives wind; focus on drainage so it does not rot.": {
        "es": "{crop} está bajo tierra y suele resistir el viento; concéntrese en el drenaje para que no se pudra.",
        "fr": "{crop} est surtout sous terre et résiste au vent ; misez sur le drainage pour éviter la pourriture.",
        "ht": "{crop} plis anba tè epi li konn reziste van; okipe drenaj pou li pa pouri."},
    "{crop} is quick to replant: harvest what is ready and keep seed for a fast restart.": {
        "es": "{crop} se vuelve a sembrar rápido: coseche lo listo y guarde semilla para empezar pronto.",
        "fr": "{crop} se replante vite : récoltez ce qui est prêt et gardez des semences pour redémarrer.",
        "ht": "{crop} fasil pou replante: rekòlte sa ki pare epi kenbe semans pou rekòmanse vit."},
    "Seedlings are fragile: hold off transplanting until the storm passes; cover nursery trays.": {
        "es": "Las plántulas son frágiles: no trasplante hasta que pase la tormenta; cubra los semilleros.",
        "fr": "Les jeunes plants sont fragiles : attendez la fin de la tempête pour repiquer ; couvrez les plateaux.",
        "ht": "Ti plant yo frajil: pa repike jiskaske tanpèt la pase; kouvri plato pepinyè yo."},
    "The field is bare: sow nothing now. After the storm, a fast cover crop protects the soil.": {
        "es": "El campo está sin cultivo: no siembre ahora. Después, un cultivo de cobertura rápido protege el suelo.",
        "fr": "La parcelle est nue : ne semez rien maintenant. Après la tempête, une culture de couverture protège le sol.",
        "ht": "Jaden an toutouni: pa simen anyen kounye a. Apre tanpèt la, yon rekòt kouvèti rapid ap pwoteje tè a."},
    "Clear field drains, culverts and outlets so water can leave quickly.": {
        "es": "Limpie drenajes, alcantarillas y salidas para que el agua salga rápido.",
        "fr": "Dégagez fossés, buses et exutoires pour que l'eau s'évacue vite.",
        "ht": "Netwaye kanal, tiyo ak sòti dlo yo pou dlo a ka sòti vit."},
    "This soil drains slowly: open extra drainage furrows at the low end of beds.": {
        "es": "Este suelo drena lento: abra surcos de drenaje extra en la parte baja de los canteros.",
        "fr": "Ce sol draine lentement : ouvrez des sillons de drainage en bas des planches.",
        "ht": "Tè sa a drene dousman: louvri plis kannal nan pati ki pi ba nan plato yo."},
    "Heavy rain is common this month: open extra drainage furrows at the low end of beds.": {
        "es": "Las lluvias fuertes son comunes este mes: abra surcos de drenaje extra en la parte baja.",
        "fr": "Les fortes pluies sont fréquentes ce mois-ci : ouvrez des sillons de drainage en bas des planches.",
        "ht": "Gwo lapli konn tonbe mwa sa a: louvri plis kannal nan pati ki pi ba yo."},
    "Sloping land ({slope}%): put residue or mulch on bare beds to cut erosion.": {
        "es": "Terreno en pendiente ({slope}%): cubra los canteros con rastrojo o mantillo para frenar la erosión.",
        "fr": "Terrain en pente ({slope} %) : paillez les planches nues pour limiter l'érosion.",
        "ht": "Tè an pant ({slope}%): kouvri plato toutouni yo ak pay pou anpeche ewozyon."},
    "Do not apply fertiliser or spray before heavy rain: it washes off and pollutes water.": {
        "es": "No aplique fertilizante ni fumigue antes de lluvias fuertes: se lava y contamina el agua.",
        "fr": "N'épandez ni engrais ni traitement avant de fortes pluies : ils sont lessivés et polluent l'eau.",
        "ht": "Pa mete angrè ni flite anvan gwo lapli: dlo ap lave l epi l ap polye dlo."},
    "Move seed, fertiliser, fuel and tools to a dry, raised, tied-down store.": {
        "es": "Guarde semilla, fertilizante, combustible y herramientas en un lugar seco, elevado y asegurado.",
        "fr": "Mettez semences, engrais, carburant et outils dans un abri sec, surélevé et bien attaché.",
        "ht": "Mete semans, angrè, gaz ak zouti nan yon kote ki sèk, ki wo epi ki byen mare."},
    "Photograph the field and crops now; it speeds up insurance and relief claims.": {
        "es": "Fotografíe el campo y los cultivos ahora; agiliza seguros y ayudas.",
        "fr": "Photographiez la parcelle et les cultures maintenant ; cela accélère assurances et aides.",
        "ht": "Pran foto jaden an ak rekòt yo kounye a; sa ap fè asirans ak èd vin pi vit."},
    "Move livestock to high ground with feed and water for three days.": {
        "es": "Lleve el ganado a terreno alto con comida y agua para tres días.",
        "fr": "Montez le bétail en hauteur avec de quoi manger et boire pour trois jours.",
        "ht": "Mennen bèt yo sou tè ki wo ak manje ak dlo pou twa jou."},
    # stages
    "seedling": {"es": "plántula", "fr": "jeune plant", "ht": "ti plant"},
    "vegetative": {"es": "crecimiento", "fr": "croissance", "ht": "kwasans"},
    "reproductive": {"es": "floración y fruto", "fr": "floraison et fruits", "ht": "flè ak fwi"},
    "mature": {"es": "madurez", "fr": "maturité", "ht": "matirite"},
    "Safety & salvage": {"es": "Seguridad y rescate", "fr": "Sécurité et sauvetage", "ht": "Sekirite ak sove sa ki rete"},
    "Drain & stabilise": {"es": "Drenar y estabilizar", "fr": "Drainer et stabiliser", "ht": "Drene ak estabilize"},
    "Cover & rebuild": {"es": "Cubrir y reconstruir", "fr": "Couvrir et reconstruire", "ht": "Kouvri ak rebati"},
    "Back to production": {"es": "De vuelta a producir", "fr": "Retour à la production", "ht": "Retounen nan pwodiksyon"},
    "Move on when": {"es": "Siga cuando", "fr": "Passez à la suite quand", "ht": "Kontinye lè"},
    # assistant
    "Ask a question about your farm…": {"es": "Haga una pregunta sobre su finca…", "fr": "Posez une question sur votre ferme…", "ht": "Poze yon kesyon sou jaden ou…"},
    "Try asking": {"es": "Pruebe a preguntar", "fr": "Essayez de demander", "ht": "Eseye mande"},
    # footer
    "FarmFit supports farmers' judgment; it never replaces it. Check plans with your extension officer.": {
        "es": "FarmFit apoya el criterio del agricultor; nunca lo reemplaza. Consulte los planes con su extensionista.",
        "fr": "FarmFit appuie le jugement des agriculteurs, sans jamais le remplacer. Vérifiez les plans avec votre conseiller agricole.",
        "ht": "FarmFit sipòte jijman kiltivatè a; li pa janm ranplase l. Tcheke plan yo ak ajan agrikòl ou."},
}


def t(text, lang="en", **kw):
    out = text if lang == "en" else T.get(text, {}).get(lang, text)
    return out.format(**kw) if kw else out


def month(i, lang="en"):
    """i: 1..12"""
    return MONTHS.get(lang, MONTHS["en"])[i - 1]
