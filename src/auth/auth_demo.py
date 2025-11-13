"""
Module de simulation d'authentification utilisateur

Dans une vraie application, ceci serait remplacé par:
- SSO (Single Sign-On)
- LDAP/Active Directory
- OAuth2
- JWT tokens
- Session utilisateur Dataiku

Pour la démo, on utilise un simple store Dash.
"""

from typing import Optional, List, Dict, Tuple


# Utilisateurs de démonstration
DEMO_USERS = {
    "jean.dupont@finance.com": {
        "name": "Jean Dupont",
        "email": "jean.dupont@finance.com",
        "groups": ["Finance"],
        "role": "user"
    },
    "marie.martin@finance.com": {
        "name": "Marie Martin",
        "email": "marie.martin@finance.com",
        "groups": ["Finance"],
        "role": "user"
    },
    "sophie.rh@example.com": {
        "name": "Sophie Leblanc",
        "email": "sophie.rh@example.com",
        "groups": ["RH"],
        "role": "user"
    },
    "paul.recruteur@example.com": {
        "name": "Paul Recruteur",
        "email": "paul.recruteur@example.com",
        "groups": ["RH"],
        "role": "user"
    },
    "pierre@marketing.com": {
        "name": "Pierre Dubois",
        "email": "pierre@marketing.com",
        "groups": ["Marketing"],
        "role": "user"
    },
    "dg@example.com": {
        "name": "Directeur Général",
        "email": "dg@example.com",
        "groups": ["Direction"],
        "role": "admin"
    },
    "admin@example.com": {
        "name": "Administrateur",
        "email": "admin@example.com",
        "groups": ["Admin"],
        "role": "admin"
    },
    "externe@autre.com": {
        "name": "Utilisateur Externe",
        "email": "externe@autre.com",
        "groups": [],
        "role": "guest"
    }
}


def get_demo_users_list() -> List[Dict]:
    """Retourne la liste des utilisateurs de démo pour le dropdown"""
    return [
        {
            "label": f"{user['name']} ({user['email']}) - {', '.join(user['groups']) if user['groups'] else 'Aucun groupe'}",
            "value": user['email']
        }
        for user in DEMO_USERS.values()
    ]


def get_user_info(email: str) -> Optional[Dict]:
    """Récupère les informations d'un utilisateur"""
    return DEMO_USERS.get(email)


def get_user_permissions(email: str) -> Tuple[str, List[str]]:
    """
    Récupère l'email et les groupes d'un utilisateur
    
    Returns:
        Tuple[email, groups]
    """
    user = get_user_info(email)
    if not user:
        return email, []
    return user['email'], user['groups']


def is_admin(email: str) -> bool:
    """Vérifie si l'utilisateur est admin"""
    user = get_user_info(email)
    return user and user.get('role') == 'admin'
