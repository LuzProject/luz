# local imports
from .luzbuild import LuzBuild

def main():
    print('here (main)')
    LuzBuild().build()
    
if __name__ == '__main__':
    main()