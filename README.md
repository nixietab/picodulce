<p align="center">
  <img src="https://github.com/nixietab/picodulce/assets/75538775/36fee78f-fb46-400c-8b14-dda5ec6191ef" alt="launcher_icon">

</p>

<h1 align="center">Picodulce Launcher</h1>

<p align="center">The simple FOSS launcher you been looking for</p>


<p align="center">
  <a href="https://github.com/nixietab/picodulce/releases">
    <img src="https://img.shields.io/github/v/release/nixietab/picodulce" alt="Latest Release">
  </a>
  <a href="https://github.com/nixietab/picodulce/issues">
    <img src="https://img.shields.io/github/issues/nixietab/picodulce" alt="Issues">
  </a>
  <a href="https://github.com/nixietab/picodulce/pulls">
    <img src="https://img.shields.io/github/issues-pr/nixietab/picodulce" alt="Pull Requests">
  </a>
  <a href="https://github.com/nixietab/picodulce/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/nixietab/picodulce" alt="License">
  </a>
  <a href="https://github.com/nixietab/picodulce">
    <img src="https://img.shields.io/github/stars/nixietab/picodulce?style=social" alt="GitHub Stars">
  </a>
</p>


  Picodulce is a feature-rich launcher for Minecraft, developed using Qt5. It serves as a graphical user interface (GUI) for the picomc project, providing users with a seamless experience in managing and launching game versions.


![imagen](https://github.com/user-attachments/assets/115b39be-47d3-4ac7-893a-5849c1e4570c)

## Key Features

- **Version Management**: Picodulce is designed to download and launch all available game versions, ensuring users have easy access to the latest updates as well as older versions.
- **Offline and Online Support**: Whether you're connected to Microsoft or not, Picodulce ensures you can still enjoy your game by supporting both offline and online modes.
- **Integrated Mod Manager**: Includes the [Marroc Mod Manager](https://github.com/nixietab/marroc), enabling users to effortlessly manage and customize their game with mods and texturepacks.
- **Custom Theme Support**: Create and apply personalized themes with ease. A dedicated repository and guide are [available to help you get started.](https://github.com/nixietab/picodulce-themes)

# Installation
If you are on windows you may be more interested in a [installer](https://github.com/nixietab/2hsu/releases/download/release/2hsu.exe)

### 1. Clone the repository

``` git clone https://github.com/nixietab/picodulce ```

### 2. (Optional) Set Up a Virtual Environment
Setting up a virtual environment is recommended to avoid dependency conflicts. Picodulce relies on the path of the `picomc` project, and using a virtual environment helps prevent errors.

Create the virtual environment:

``` python -m venv venv ```

- **Linux/Mac:**  
  `source venv/bin/activate`
- **Windows:**  
  `.\\venv\\Scripts\\activate`
 


### Install requirements

Now on the venv you can install the requirements safely

```pip install -r requirements.txt ```

### Running the launcher

On the venv run it as a normal python script

```python picodulce.py```

Just make sure you have Java installed for running the actual game

### About the name
The name "Picodulce" comes from a popular Argentinian candy. This reflects the enjoyable and user-friendly experience that the launcher aims to provide, making game management straightforward and pleasant.
