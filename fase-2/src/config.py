"""Contrato del problema: columnas y valores por defecto.

Es el único lugar donde se definen las columnas; train.py, predict.py y los
tests lo reutilizan. Es el mismo contrato de la fase 1 (UNSW-NB15).
"""

TARGET = "label"
# id = identificador; attack_cat = fuga del objetivo (describe el ataque ya ocurrido)
COLUMNAS_EXCLUIR = ["id", "attack_cat"]
CLASES = {"0": "normal", "1": "ataque"}

COLS_CATEGORICAS = ["proto", "service", "state"]
COLS_NUMERICAS = [
    "dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sttl", "dttl", "sload", "dload",
    "sloss", "dloss", "sinpkt", "dinpkt", "sjit", "djit", "swin", "stcpb", "dtcpb", "dwin",
    "tcprtt", "synack", "ackdat", "smean", "dmean", "trans_depth", "response_body_len",
    "ct_srv_src", "ct_state_ttl", "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm",
    "ct_dst_src_ltm", "is_ftp_login", "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm",
    "ct_srv_dst", "is_sm_ips_ports",
]
COLS_ENTRADA = COLS_NUMERICAS + COLS_CATEGORICAS

# Valores por defecto de los argumentos de train.py
SEED = 42
TEST_SIZE = 0.2
CV_FOLDS = 3
ESTIMADORES_DISPONIBLES = ["logreg", "random_forest"]
METRICA = "f1"  # F1 de la clase 1 (ataque)

NOMBRE_MODELO = "modelo.joblib"
NOMBRE_METRICAS = "metrics.json"
NOMBRE_METADATA = "metadata.json"
