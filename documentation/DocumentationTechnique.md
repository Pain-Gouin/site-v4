# Documentation détaillée du site Pain'Gouin

Dernière mise à jour : 13/08/2024 par Mathis Rimbert

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

