# Documentation détaillée du site Pain'Gouin

## Déploiement
### Test près-déploiement
Le site est déployé à l'aide d'un conteneur Docker contenant : tout le code source, un serveur Django de production (gunicorn) ainsi qu'un service pour servir les fichiers statiques (whitenoise).

Bien que ce ne soit pas une bonne pratique, les mots de passe pour la base de donnée sont inclus dans le conteneur, afin de simplifier le déploiement.

Avant de déployer une version, il est important de tester le bon fonctionnement de l'image docker. Pour cela, copier le fichier `compose.template.yaml` vers `compose.yaml`, en l'adaptant à son environnement de développement, et en lançant la construction et le déploiement en local de l'image à l'aide de la commande :
```console
docker compose up --build
```

> [!IMPORTANT] 
> Pour tester l'image telle qu'elle sera déployé, bien désactiver le debug dans le docker compose !

Le site devrait alors être accessible à l'adresse http://127.0.0.1:8000/.

> [!NOTE] 
> Si de nouvelles librairies sont nécéssaires, il faut bien penser à mettre à jour le fichier `requirements.txt` à l'aide de la commande `pip freeze`.  
> Le fichier `requirement.minimal.txt` est sensé contenir uniquement les dépendances primaire, et est utile pour la mise à jour des dépendances.

### Déploiement sur l'infrastructure de Rézoléo

**Après avoir testé le bon fonctionnement**, vous pouvez push vos changements sur la branche `prod`. Cela déclenchera une action Github, qui va automatiquement construire et uploader une image sur le GHCR. Un Watchtower sur les serveurs de Rézoléo devrait détecter cette nouvelle image, et automatiquement mettre à jour puis redéployer le conteneur tournant sur leurs serveurs.

> [!IMPORTANT] 
> En cas de migration de la base de donnée, la commande `python manage.py migrate` s'exécute automatiquement au lancement du conteneur mise à jour.  
> Il faut bien avoir commit les migrations après les avoir générés à l'aide de la commande `python manage.py makemigrations`, et faire attention à ce qu'elle ne provoque pas de perte de données.  
> **Il est recommandé de faire un backup de la BD avant tout déploiement !**

Le conteneur utilise le serveur mySQL du rézo. Le docker compose le générant ainsi que les fichiers media se situent sur l'accès SFTP.

## Identifiants de connexion
Pain'Gouin est hébergé par l'association Rézoléo, en cas de problèmes d'hébergements, il ne faut pas hésiter à les contacter. 

L'association Pain'Gouin dispose de deux images Docker, une première de développement et disponible à l'URL : paingouindev.rezoleo.fr et la deuxième pour le site utilisé en production à l'adresse : paingouin.rezoleo.fr. **Il est essentiel de s'assurer que le site fonctionne sur l'espace de développement avant de le basculer en production.**

Les identifiants de connexion au serveur SFTP des deux images sont : 

 - URL : sftp.rezoleo.fr
 - Port : 8888 (si connexion extérieur à la résidence sinon 22)
 - Utilisateur : paingouin
 - Mot de passe : ***REMOVED***

Les identifiants de connexion à l'interface PHPMyAdmin des deux images sont : 

 - URL : phpmyadmin.rezoleo.fr
 - Utilisateur : paingouin
 - Mot de passe : ***REMOVED***

Les identifiants de connexion à MySQL sont donc les mêmes avec pour hôte : mysql.rezoleo.fr
Les identifiants associés aux différents mails pouvant être utilisés par le site sont disponibles sur le Drive de l'association. 

## Structure du code

    📦site-v4
     ┣ 📂commande               // application de gestion des commandes
     ┣ 📂media                  // fichiers importé par l'utilisateur
     ┣ 📂paingouin		        // fichiers de base du projet
     ┣ 📂theme                  // style utilisé par TailwindCSS
     ┗ 📜README.md              // fichier README...

## Structure de la base de donnée
La base de donnée de l'application commande est représentée de la manière suivante (image ci-dessous), pour voir comment les modèles sont interprétés par Django, vous pouvez vous référez au fichier commande/models.py qui répertorie les modèles utilisés par le site. 
![SchémaDB](SchemaDB.png)
Ce schéma n'est pas une représentation réelle de toute la base de donnée, Django a ses propres tables et la table utilisateur dérive d'une table de base de Django. Si vous êtes curieux, vous pouvez directement voir la base de donnée via le panel PHPMyAdmin. 

## TailwindCSS

La version 3 de tailwind est utilisée. Elle est intégrée à Django à l'aide de la librairie [django-tailwind](https://github.com/timonweb/django-tailwind).  
Pour développer avec tailwind, il est nécessaire d'utiliser la commande `python manage.py tailwind dev` au lieu de la commande `python manage.py runserver`. Cela permet d'automatiquement mettre à jour le fichier de style lorsqu'une page HTML est éditée, afin d'inclure les potentielles nouvelles fonctionnalités utilisées.  
En effet, seules les fonctionnalités de tailwind utilisées par le site web sont incluses dans la feuille de style, pour réduire sa taille.  
Avant "déploiement", il est nécessaire d'utiliser la commande `python manage.py tailwind build`, pour générer une feuille de style optimisée pour la prod, juste avant d'utiliser la commande `python manage.py collectstatic`. Cette étape est effectuée automatiquement lorsque le conteneur docker est utilisé.
