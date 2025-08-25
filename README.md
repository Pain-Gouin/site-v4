# Documentation site Pain'Gouin

## Introduction
Bienvenue dans cette documentation sur la quatrième version du site de l'association. Cette version a été initialement développée en 2024 par [Mathis Rimbert](https://github.com/mrimbert). Elle répond à plusieurs besoins notamment celui d'obtenir un site plus "moderne" que le précédent ainsi que de passer sur une architecture plus propre et plus compréhensive. 

Cette documentation se divise en deux fichiers, le premier (celui-ci) traitera des affaires courantes du responsable web, des perspectives pour développer le site, de l'architecture général du site, ainsi que quelques tutoriels pour bien développer sur le site de Pain'Gouin. La deuxième partie traitera de l'architecture du repo. 

Ce site a été réalisé (et est géré) par des autodidactes et non par des professionnels, il s'agit donc d'une usine à gaz, il faut faire attention à ce qu'on fait et ne pas hésiter à poser des questions en cas de doute. Je m'excuse pour tous les problèmes futurs que le site pourrait causer ! 

## Généralités sur le site

Ce site a été développé à l'aide du framework Django. C'est un framework Python conçu pour faciliter le développement de site web sécurisé. Ce framework a été choisi pour faciliter les modifications du site web par les futurs responsables web, Python étant un langage bien mieux connu (notamment par la classe préparatoire) que PHP. Si vous désirez vous former à l'utilisation de ce framework, [la documentation officielle](https://docs.djangoproject.com/fr/5.1/) est de très bonne qualité en plus d'être disponible en français. 

En ce qui concerne le style, le site utilise Tailwind CSS et l'implémente dans le projet à l'aide de library django-tailwind. Encore une fois, [la documentation officielle](https://tailwindcss.com/docs/installation) de Tailwind CSS est de très bonne qualité. 

## Guide de passations
Lors d'une passation du bureau, il est nécessaire de mettre à jour certaines informations du site. Toutes les modifications peuvent se faire directement depuis GitHub, avec des connaissances simples en HTML.

Il faut mettre à jour la page des mentions légales, avec le nouveau responsable de la publication, et le nouveau responsable web. Cela se fait [ici](https://github.com/Pain-Gouin/site-v4/blob/master/commande/templates/commande/mentions.html), en éditant le fichier depuis l'interface web.

Il faut ensuite déployer les changements, en poussant les modifications sur la branche de production. Pour se faire, aller [ici](https://github.com/Pain-Gouin/site-v4/compare/prod...master), cliquer sur `Create pull request`, puis confirmer la création du pull request.

Il ne vous reste plus qu'à confirmer le Pull request, ce qui mettra à jour la branche `prod`. Les changements devraient alors automatiquement être mise à jour sur le site en production, après **Insérer ici la durée quand ce sera opérationnel**.

## Comment développer sur le site ?

Pour apporter des modifications sur le site, voici un petit tutoriel. J'utilise ici la distribution Ubuntu (mais rien ne change sous Windows généralement). Il faut vous assurer de posséder sur votre machine Git et Python. Créer un dossier spécial pour le projet. 

### Récupération du repo GitHub
Pour récupérer le contenu du repo, il suffit de le cloner.

### Mise en place de l'environnement virtuel
Pour développer dans de bonnes conditions, il faut mettre en place un environnement virtuel (ou venv), cela permet d'installer toutes les librairies dont nous aurons besoin dans un endroit à part afin d'éviter qu'elles interagissent avec d'autres librairies que vous auriez pu installer sur votre machine (et permettre aussi de lister proprement les librairies dont le projet a besoin pour fonctionner).  
Pour ce faire dans le dossier exécuter la commande : 
```console
python -m venv .venv
```
Cela crée un environnement virtuel Python intitulé `.venv`.  
Puis, entrons dans l'environnement avec la commande :
- Linux
```console
source .venv/bin/activate
```
- Windows
```console
.venv/Scripts/activate.bat
```
On va désormais pouvoir travailler tranquillement et pouvoir installer toutes les librairies dont le site a besoin pour fonctionner à l'aide de la commande : 
```console
pip install -r requirements.txt
```
### Mise en place de NodeJS et de TailwindCSS
Afin d'utiliser TailwindCSS, il faut installer NodeJS (22 au moment d'écrire ces lignes). Pour Linux, vous pouvez utiliser ce [site](https://nodesource.com/products/distributions).  
### Démarrer le serveur local
Une fois tout ceci fait, il faut configurer le site pour tourner sur sa machine local. Pour ce faire, copiez le fichier `paingouin/settings.template.py` vers `paingouin/settings.py`, et modifiez-le pour correspondre à votre base de donnée locale. Vous devez modifier les informations suivantes : 

```Python
DATABASES = {
'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': '<nom de la base>',
    'HOST': '<ip de la base de donnée>',
    'PORT': '<port>',
    'USER': '<utilisateur de la base>',
    'PASSWORD': '<mot de passe>',
    'OPTIONS':{
    "init_command": "SET foreign_key_checks = 0;",
    }
},
}
```

Pour créer une base de donnée en local vous pouvez utiliser l'outil Docker, Rézoléo peut fournir une formation pour l'utilisation de cet outil en cas de problème.  
Une fois les informations modifiées, exécutez les commandes suivantes : 
```console
python manage.py makemigrations
python manage.py migrate
 ```   
Vous venez de mettre en place les différentes tables dont le site (et Django) a besoin pour fonctionner.  
Il faut maintenant initialiser TailwindCSS. Pour ce faire, utilisez la commande suivante :
```console
python manage.py tailwind install
```
Il ne vous reste plus qu'à démarrer le serveur local avec la commande : 
```console
python manage.py tailwind dev
```
Le serveur est désormais lancé et vous n'avez qu'à cliquer sur le lien renvoyé dans la console par Django pour y accéder. 
> [!NOTE] 
> Pour savoir pourquoi cette commande est utilisée au lieu du traditionel `python manage.py runserver`, rendez-vous dans la [Documentation Technique](documentation/DocumentationTechnique.md) à la section traitant de Tailwind.

### Créer un administrateur local sur le site
Pour créer un utilisateur ayant les permissions super-admin sur le site exécutez dans la console la commande suivante : 
```console
python manage.py createsuperuser
```
 Puis suivez les informations renvoyées dans la console pour créer l'utilisateur. 

## Déploiement

Cf la [Documentation Technique](documentation/DocumentationTechnique.md)

## Axes d'amélioration du site

Le site n'est actuellement pas parfait (il est même bien loin de l'être), le code n'est pas forcément organisé de manière très propre (et je m'excuse pour ça) et il manque de commentaires. L'un des axes d'amélioration est donc de rendre le site le plus clair possible pour permettre à n'importe qui de modifier le site sans souci. Il est donc essentiel de documenter du mieux possible toutes les fonctionnalités ajoutées et de mettre à jour la documentation le plus souvent possible dès lors qu'une modification importante a été apportée au site (cf. date de mise à jour du document).

Entre autres, voici une liste de choses à faire sur le site (pour le rendre encore meilleur) : 

 - [ ] Ajout de l'option "Pain tranché", "Pain non tranché" dans les produits et les commandes
 - [ ] Gérer les quotas des produits et empêcher la commande d'un produit dont le quota journalier est atteint
 - [ ] Rendre l'application PWA (ie. application mobile)
 - [ ] Ajouter la modification de commande de n'importe quel utilisateur sur le panel admin
 - [ ] Exporter directement des factures format PDF dans le panel admin
 - [ ] Modifier le style de certaines pages un peu trop simpliste (espace livreur par exemple) pour les rendre plus sympas (subjectif)

## En attendant la modification de commande automatisée sur le panel admin
Si une livraison se passe mal (ce qui n'arrive jamais hein...) et qu'un produit venait à ne pas être livré, pour rembourser un utilisateur, voici la marche à suivre : 

 - Trouver la commande de l'utilisateur sur le panel admin et retirer le produit concerné de sa commande (en se connectant directement au panel PHPMyAdmin à l'aide des identifiants donnés dans la documentation détaillée)
 - Le rembourser à la main du prix du produit retiré de sa commande
 - Le prévenir que le remboursement a été effectué 

Si un problème survient, ou s'il y a des doutes, ne pas hésiter à contacter [Mathis Rimbert](https://www.facebook.com/profile.php?id=61550914982995)
