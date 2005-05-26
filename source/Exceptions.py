
class BootManagerException(Exception):
    def __init__( self, err ):
        self.__fault= err

    def __str__( self ):
        return self.__fault
    
