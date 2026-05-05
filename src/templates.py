# Messages envoyés aux personnes qui ont liké un article
PROMO_LIKER = """Bonjour {username} ! 👋

J'ai remarqué que vous avez ajouté "{item_title}" à vos favoris. 🤩

J'ai des offres spéciales en ce moment :
✅ -10% de réduction pour les abonnés à mon profil
✅ -20% de réduction à partir de 3 paires achetées

Si cet article vous intéresse, n'hésitez pas à me faire une offre ou à me contacter directement ! 😊

Bonne journée !"""

# Réponses automatiques selon le mot-clé détecté dans le message reçu
KEYWORD_RESPONSES = {
    "état": (
        "Bonjour ! 😊 L'article est en excellent état, soigneusement entretenu. "
        "Toutes les imperfections éventuelles sont visibles sur les photos. "
        "N'hésitez pas si vous avez d'autres questions !"
    ),
    "livraison": (
        "Bonjour ! 😊 J'envoie les colis sous 2 à 3 jours ouvrés après la commande. "
        "L'envoi se fait via Vinted (Mondial Relay, Colissimo, etc.) selon votre choix. "
        "Tout est suivi et sécurisé !"
    ),
    "taille": (
        "Bonjour ! 😊 La taille est indiquée dans l'annonce. "
        "Si vous souhaitez les mesures exactes (tour de taille, longueur, etc.), "
        "je peux vous les donner. N'hésitez pas à demander !"
    ),
    "mesure": (
        "Bonjour ! 😊 Je peux vous donner toutes les mesures souhaitées. "
        "Dites-moi ce dont vous avez besoin (tour de poitrine, taille, longueur, etc.) "
        "et je vous réponds rapidement !"
    ),
    "prix": (
        "Bonjour ! 😊 Le prix indiqué est ferme, mais j'offre des réductions : "
        "-10% aux abonnés à mon profil et -20% à partir de 3 articles achetés ! "
        "N'hésitez pas à grouper vos achats. 😉"
    ),
    "négocia": (
        "Bonjour ! 😊 Le prix est fixe, mais j'offre -10% aux abonnés "
        "et -20% à partir de 3 articles. "
        "N'hésitez pas à faire une offre groupée si d'autres articles vous intéressent !"
    ),
    "disponible": (
        "Bonjour ! 😊 Oui, l'article est toujours disponible ! "
        "N'hésitez pas à le commander directement ou à me contacter si vous avez des questions."
    ),
    "paiement": (
        "Bonjour ! 😊 Le paiement se fait directement via Vinted de manière sécurisée. "
        "Je n'accepte aucun paiement en dehors de la plateforme pour votre protection."
    ),
    "défaut": (
        "Bonjour ! 😊 L'article n'a pas de défaut visible. "
        "Les photos sont représentatives de l'état réel. "
        "Si vous souhaitez des photos supplémentaires, je peux vous en envoyer !"
    ),
    "abonné": (
        "Bonjour ! 😊 Exactement ! En vous abonnant à mon profil, vous bénéficiez de -10% "
        "sur tous mes articles. Et à partir de 3 articles achetés, c'est -20% ! "
        "N'hésitez pas à parcourir mes autres annonces. 🛍️"
    ),
}

# Réponse par défaut si aucun mot-clé n'est trouvé
DEFAULT_RESPONSE = (
    "Bonjour ! 😊 Merci pour votre message. Je vous réponds dans les plus brefs délais !\n\n"
    "En attendant, sachez que je propose :\n"
    "✅ -10% pour les abonnés à mon profil\n"
    "✅ -20% à partir de 3 articles achetés\n\n"
    "N'hésitez pas à parcourir mes autres annonces ! 🛍️"
)
