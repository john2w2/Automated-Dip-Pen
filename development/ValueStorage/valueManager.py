import os

class TupleStorageManager:
    """
    A tuple storage manager stores and loads a
    tuple from disk. This can be used to 
    persist locations through multiple
    experiments
    """

    def __init__(self,
                 calib_dir: str,
                 default_values: tuple[float, float],
                 file_name:str):
        """
        Instantiates a new TupleStorageManager that 
        manages file_name in calib_dir. If file_name
        does not exist in calib_dir, one will be created
        with default_values upon the first call to loadValues()
        if file_name doesn't exist.

        :param calib_dir: Path to the directory in which data is stored
        :type calib_dir: str
        :param default_values: A tuple of default values for this manager.
                        Used if the file is corrupted
        :type default_values: tuple[float, float]
        :param file_name: the name of the file in which to store the tuple
        :type file_name: str
        """
        self.__calib_dir: str = calib_dir
        self.__default_values: tuple[float, float] = default_values
        self.__file_name: str = file_name

    def load_values(self) -> tuple[float, float]:
        """
        Returns previously saved values that are
        stored in the file_name passed to the constructor
        of this storage manager
        If file_name does not exist, one storing the 
        default values is created and those
        default values are returned
        """

        raise NotImplementedError()
    
    def save_new_values(self, values: tuple[float, float]):
        """
        Store new values in this storage manager's file
        If this storage manager's file does not exist,
        one is created with the new values

        :param values: The new values to store in this 
        storage manager's file
        :type tuple: tuple[float, float]
        """

    def restore_default_values(self):
        """
        Resets the values in this storage manager's
        file to the default values passed to the constructor
        """
    
