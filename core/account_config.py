import os
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)

ACCOUNT_CONFIG_PATH = "config_accounts.json"


def load_account_config() -> dict:
    if not os.path.exists(ACCOUNT_CONFIG_PATH):
        return {}
    with open(ACCOUNT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_account_config(data: dict):
    with open(ACCOUNT_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_naver_api_client():
    """설정 파일에서 client_id/secret을 읽어 NaverCommerceAPI 인스턴스 생성"""
    from modules.product_releaser.naver_api import NaverCommerceAPI
    config = load_account_config()
    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")
    if not client_id or not client_secret:
        raise ValueError("커머스API 키가 설정되지 않았습니다. [계정 연동 관리]에서 먼저 등록해 주세요.")
    return NaverCommerceAPI(client_id=client_id, client_secret=client_secret)


class AccountConfigDialog(QDialog):
    """커머스API 키 + 상품등록 기본값(출고지/반품지/AS전화) 설정.
    vendor_collector_page.py의 SearchApiConfigDialog와 같은 패턴."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("계정 연동 관리")
        self.resize(460, 320)
        self.setStyleSheet("background-color: #2b2d30; color: #bcbec4;")

        layout = QVBoxLayout(self)
        desc = QLabel("커머스API 키와 상품등록 기본값을 설정합니다.")
        desc.setStyleSheet("color: #8c8e94; font-size: 12px;")
        layout.addWidget(desc)

        form = QFormLayout()
        self.id_input = QLineEdit()
        self.secret_input = QLineEdit()
        self.secret_input.setEchoMode(QLineEdit.Password)
        self.outbound_input = QLineEdit()
        self.return_input = QLineEdit()
        self.as_tel_input = QLineEdit()

        for w in (self.id_input, self.secret_input, self.outbound_input,
                  self.return_input, self.as_tel_input):
            w.setStyleSheet(
                "background-color: #1e1f22; color: #ffffff; padding: 6px;"
                " border: 1px solid #393b40; border-radius: 4px;"
            )

        form.addRow("Client ID:", self.id_input)
        form.addRow("Client Secret:", self.secret_input)
        form.addRow("출고지 주소 ID:", self.outbound_input)
        form.addRow("반품지 주소 ID:", self.return_input)
        form.addRow("A/S 전화번호:", self.as_tel_input)
        layout.addLayout(form)

        btn_save = QPushButton("저장")
        btn_save.setStyleSheet(
            "background-color: #3574f0; color: white; padding: 10px; font-weight: bold; border-radius: 4px;"
        )
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)

        self.load_config()

    def load_config(self):
        config = load_account_config()
        self.id_input.setText(config.get("client_id", ""))
        self.secret_input.setText(config.get("client_secret", ""))
        self.outbound_input.setText(str(config.get("outbound_location_id", "")))
        self.return_input.setText(str(config.get("return_location_id", "")))
        self.as_tel_input.setText(config.get("as_telephone", ""))

    def save_config(self):
        data = load_account_config()
        data.update({
            "client_id": self.id_input.text().strip(),
            "client_secret": self.secret_input.text().strip(),
            "outbound_location_id": self.outbound_input.text().strip(),
            "return_location_id": self.return_input.text().strip(),
            "as_telephone": self.as_tel_input.text().strip(),
        })
        save_account_config(data)
        QMessageBox.information(self, "저장 완료", "계정 설정이 저장되었습니다.")
        self.accept()