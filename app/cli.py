'''
Add custom commands to Flask to run tasks.
Click is used for command-line operations.
'''
import os
import click
'''
current_app does not work in this case because these commands are registered at start up, not during the handling of a request, which is the only time when current_app can be used. To remove the reference to app in this module, this trick  moves these custom commands inside a register() function that takes the app instance as an argument.
'''


def register(app):
    '''
    Create flask translate command, which is a root for several more commands.
    The help string is the docstring.
    This is a parent command, so do nothing.
    '''
    @app.cli.group()
    def translate():
        """Translation and localization commands."""
        pass

    # Add subcommand to the translate command using the decorator.
    """flask translate update"""
    @translate.command()
    def update():
        """Update all languages."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d app/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    """flask translate compile"""
    @translate.command()
    def compile():
        """Compile all languages."""
        if os.system('pybabel compile -d app/translations'):
            raise RuntimeError('compile command failed')

    # A more complicated CLI that takes an argument.
    """flask translate init LANG"""
    @translate.command()
    @click.argument('lang')
    def init(lang):
        """Initialize a new language."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel init -i messages.pot -d app/translations -l ' +
                     lang):
            raise RuntimeError('init command failed')
        os.remove('messages.pot')