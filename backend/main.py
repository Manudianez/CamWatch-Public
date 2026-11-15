from .config import Config
from .logger import logger
from .database import initialize_database
from .model_manager import add_model, list_models

from rich.console import Console
from rich.table import Table

console = Console()


def show_models():
    table = Table(title="Modelos registrados")

    table.add_column("ID", style="cyan")
    table.add_column("Usuario", style="green")
    table.add_column("Plataforma")
    table.add_column("Estado")

    models = list_models()

    if not models:
        console.print("\n[yellow]No hay modelos registrados.[/yellow]\n")
        return

    for model in models:
        table.add_row(
            str(model[0]),
            model[1],
            model[2],
            model[3]
        )

    console.print(table)


def main():
    console.rule(f"[bold cyan]{Config.APP_NAME} v{Config.VERSION}")

    initialize_database()

    while True:

        console.print("\n[bold cyan]Menú principal[/bold cyan]")
        console.print("1. Añadir modelo")
        console.print("2. Mostrar modelos")
        console.print("3. Salir")

        option = input("\nSeleccione una opción: ")

        if option == "1":

            username = input("Nombre del modelo: ").strip()

            if username:
                if add_model(username):
                    logger.info(f"Modelo '{username}' añadido correctamente")
                else:
                    logger.warning(f"El modelo '{username}' ya estaba registrado.")
            else:
                logger.warning("Debe introducir un nombre.")

        elif option == "2":

            show_models()

        elif option == "3":

            console.print("\n¡Hasta pronto, Manu! 👋")
            break

        else:

            logger.warning("Opción no válida.")


if __name__ == "__main__":
    main()