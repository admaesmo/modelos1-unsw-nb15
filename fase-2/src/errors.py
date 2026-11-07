"""Errores propios: los scripts los capturan y salen con código distinto de cero."""


class AppError(Exception):
    """Error previsible (dato, modelo o versión inválidos) con mensaje comprensible."""


class DatosInvalidosError(AppError):
    pass


class VersionExistenteError(AppError):
    pass


class ModeloNoEncontradoError(AppError):
    pass
