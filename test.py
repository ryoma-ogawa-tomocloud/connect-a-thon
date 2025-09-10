#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コネクタソン環境設定対応 DICOM MODテストコード
AM、IM、OFの設定を動的に変更可能
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from pydicom.dataset import Dataset
from pynetdicom import AE

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DICOMConnectionStatus(Enum):
    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

@dataclass
class DICOMSystemConfig:
    system_name: str
    facility_name: str
    ip_address: str
    port: int
    ae_title: str
    role: str  # AM, IM, OF
    status: DICOMConnectionStatus = DICOMConnectionStatus.UNKNOWN
    last_check: Optional[float] = None
    response_time: Optional[float] = None

class ConnectathonConfig:
    """コネクタソン設定管理クラス"""
    
    def __init__(self):
        self.systems = {}
        self.load_default_config()
    
    def load_default_config(self):
        """デフォルト設定をロード"""
        # デフォルト設定（後で変更可能）
        default_configs = [
            {
                "system_name": "LT monitor pro",
                "facility_name": "Chiba Univ",
                "ip_address": "localhost",
                "port": 11112,
                "ae_title": "LTMONITOR",
                "role": "AM"
            },
            {
                "system_name": "IM", 
                "facility_name": "Chiba Univ",
                "ip_address": "localhost",
                "port": 11113,
                "ae_title": "IM",
                "role": "IM"
            },
            {
                "system_name": "OF",
                "facility_name": "Chiba Univ", 
                "ip_address": "localhost",
                "port": 11114,
                "ae_title": "OF",
                "role": "OF"
            }
        ]
        
        for config in default_configs:
            self.add_system(**config)
    
    def add_system(self, system_name: str, facility_name: str, ip_address: str, 
                   port: int, ae_title: str, role: str):
        """システム設定を追加"""
        self.systems[role] = DICOMSystemConfig(
            system_name=system_name,
            facility_name=facility_name,
            ip_address=ip_address,
            port=port,
            ae_title=ae_title,
            role=role
        )
        logger.info(f"Added {role} system: {ae_title} at {ip_address}:{port}")
    
    def update_system(self, role: str, **kwargs):
        """システム設定を更新"""
        if role in self.systems:
            for key, value in kwargs.items():
                if hasattr(self.systems[role], key):
                    setattr(self.systems[role], key, value)
                    logger.info(f"Updated {role} {key}: {value}")
    
    def get_system(self, role: str) -> Optional[DICOMSystemConfig]:
        """システム設定を取得"""
        return self.systems.get(role)
    
    def list_systems(self) -> Dict[str, DICOMSystemConfig]:
        """全システム設定を取得"""
        return self.systems.copy()
    
    def save_config(self, filename: str = "connectathon_config.json"):
        """設定をJSONファイルに保存"""
        config_data = {}
        for role, system in self.systems.items():
            config_data[role] = {
                "system_name": system.system_name,
                "facility_name": system.facility_name,
                "ip_address": system.ip_address,
                "port": system.port,
                "ae_title": system.ae_title,
                "role": system.role
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration saved to {filename}")
    
    def load_config(self, filename: str = "connectathon_config.json"):
        """JSONファイルから設定をロード"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.systems.clear()
            for role, config in config_data.items():
                self.add_system(**config)
            
            logger.info(f"Configuration loaded from {filename}")
        except FileNotFoundError:
            logger.warning(f"Config file {filename} not found, using defaults")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

class DICOMTestClient:
    """DICOM テストクライアントクラス"""
    
    def __init__(self, client_ae_title: str = "MODTEST"):
        self.client_ae_title = client_ae_title
        self.ae = AE(ae_title=client_ae_title)
        
        # サポートするSOPクラスを追加
        verification_uid = '1.2.840.10008.1.1'  # Verification SOP Class
        find_uid = '1.2.840.10008.5.1.4.1.2.2.1'  # Study Root Query/Retrieve - FIND
        move_uid = '1.2.840.10008.5.1.4.1.2.2.2'  # Study Root Query/Retrieve - MOVE
        store_uid = '1.2.840.10008.5.1.4.1.1.2'   # CT Image Storage
        
        self.ae.add_requested_context(verification_uid)
        self.ae.add_requested_context(find_uid)
        self.ae.add_requested_context(move_uid)
        self.ae.add_requested_context(store_uid)
    
    async def c_echo(self, target_ip: str, target_port: int, target_ae: str) -> tuple[bool, float]:
        """DICOM C-ECHOテスト（接続確認）"""
        start_time = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            assoc = await loop.run_in_executor(
                None, 
                self.ae.associate, 
                target_ip, 
                target_port, 
                target_ae
            )
            
            if assoc.is_established:
                status = await loop.run_in_executor(None, assoc.send_c_echo)
                await loop.run_in_executor(None, assoc.release)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if status.Status == 0x0000:
                    return True, response_time
                else:
                    logger.warning(f"C-ECHO failed with status: 0x{status.Status:04X}")
                    return False, response_time
            else:
                end_time = time.time()
                logger.error("Association establishment failed")
                return False, end_time - start_time
                
        except Exception as e:
            end_time = time.time()
            logger.error(f"C-ECHO error: {str(e)}")
            return False, end_time - start_time

class ConnectathonDICOMTester:
    """コネクタソン DICOM テスタークラス"""
    
    def __init__(self, config: ConnectathonConfig = None):
        self.config = config or ConnectathonConfig()
        self.client = DICOMTestClient()
    
    async def test_system_connection(self, role: str) -> bool:
        """指定システムの接続テスト"""
        system = self.config.get_system(role)
        if not system:
            logger.error(f"System {role} not configured")
            return False
        
        try:
            success, response_time = await self.client.c_echo(
                system.ip_address, 
                system.port, 
                system.ae_title
            )
            
            system.last_check = time.time()
            system.response_time = response_time
            
            if success:
                system.status = DICOMConnectionStatus.CONNECTED
                logger.info(f"{role} ({system.ae_title}) connection: SUCCESS ({response_time:.3f}s)")
                return True
            else:
                system.status = DICOMConnectionStatus.DISCONNECTED
                logger.warning(f"{role} ({system.ae_title}) connection: FAILED ({response_time:.3f}s)")
                return False
                
        except Exception as e:
            system.status = DICOMConnectionStatus.ERROR
            system.last_check = time.time()
            logger.error(f"{role} connection error: {str(e)}")
            return False
    
    async def test_all_systems(self) -> Dict[str, bool]:
        """全システムの接続テスト"""
        results = {}
        for role in self.config.list_systems().keys():
            results[role] = await self.test_system_connection(role)
        return results
    
    async def get_system_status(self) -> Dict[str, Any]:
        """全システムのステータス取得"""
        status = {
            "timestamp": time.time(),
            "client_ae_title": self.client.client_ae_title,
            "systems": {}
        }
        
        for role, system in self.config.list_systems().items():
            status["systems"][role] = {
                "system_name": system.system_name,
                "facility_name": system.facility_name,
                "ip_address": system.ip_address,
                "port": system.port,
                "ae_title": system.ae_title,
                "role": system.role,
                "status": system.status.value,
                "last_check": system.last_check,
                "response_time": system.response_time
            }
        
        return status
    
    async def run_monitoring_cycle(self, interval: int = 60, cycles: int = None):
        """定期監視サイクル実行"""
        logger.info(f"Starting monitoring cycle (interval: {interval}s)")
        
        cycle_count = 0
        while cycles is None or cycle_count < cycles:
            cycle_count += 1
            logger.info(f"=== Monitoring Cycle #{cycle_count} ===")
            
            # 全システムの接続テスト
            results = await self.test_all_systems()
            
            # 結果表示
            for role, success in results.items():
                system = self.config.get_system(role)
                status = "PASS" if success else "FAIL"
                response_time = system.response_time if system.response_time else 0
                logger.info(f"  {role} ({system.ae_title}): {status} ({response_time:.3f}s)")
            
            logger.info(f"=== Cycle #{cycle_count} Complete ===")
            
            if cycles is None or cycle_count < cycles:
                await asyncio.sleep(interval)

class InteractiveConfigManager:
    """対話式設定管理クラス"""
    
    def __init__(self, config: ConnectathonConfig):
        self.config = config
    
    def interactive_setup(self):
        """対話式でシステム設定"""
        print("\n=== Connectathon DICOM System Configuration ===")
        print("Current configuration:")
        self.display_current_config()
        
        while True:
            print("\nOptions:")
            print("1. Update AM configuration")
            print("2. Update IM configuration") 
            print("3. Update OF configuration")
            print("4. Display current configuration")
            print("5. Save configuration to file")
            print("6. Load configuration from file")
            print("7. Continue with testing")
            print("0. Exit")
            
            choice = input("\nSelect option (0-7): ").strip()
            
            if choice == "1":
                self.update_system_config("AM")
            elif choice == "2":
                self.update_system_config("IM")
            elif choice == "3":
                self.update_system_config("OF")
            elif choice == "4":
                self.display_current_config()
            elif choice == "5":
                filename = input("Enter filename (default: connectathon_config.json): ").strip()
                if not filename:
                    filename = "connectathon_config.json"
                self.config.save_config(filename)
            elif choice == "6":
                filename = input("Enter filename (default: connectathon_config.json): ").strip()
                if not filename:
                    filename = "connectathon_config.json"
                self.config.load_config(filename)
            elif choice == "7":
                break
            elif choice == "0":
                exit(0)
            else:
                print("Invalid option. Please try again.")
    
    def display_current_config(self):
        """現在の設定を表示"""
        print("\nCurrent System Configuration:")
        print("-" * 60)
        for role, system in self.config.list_systems().items():
            print(f"{role}:")
            print(f"  System Name: {system.system_name}")
            print(f"  Facility: {system.facility_name}")
            print(f"  IP Address: {system.ip_address}")
            print(f"  Port: {system.port}")
            print(f"  AE Title: {system.ae_title}")
            print()
    
    def update_system_config(self, role: str):
        """システム設定を更新"""
        system = self.config.get_system(role)
        if not system:
            print(f"System {role} not found")
            return
        
        print(f"\n=== Update {role} Configuration ===")
        print(f"Current settings:")
        print(f"  IP Address: {system.ip_address}")
        print(f"  Port: {system.port}")
        print(f"  AE Title: {system.ae_title}")
        
        # IP Address
        new_ip = input(f"Enter new IP address (current: {system.ip_address}): ").strip()
        if new_ip:
            self.config.update_system(role, ip_address=new_ip)
        
        # Port
        new_port = input(f"Enter new port (current: {system.port}): ").strip()
        if new_port:
            try:
                port_num = int(new_port)
                self.config.update_system(role, port=port_num)
            except ValueError:
                print("Invalid port number")
        
        # AE Title
        new_ae = input(f"Enter new AE title (current: {system.ae_title}): ").strip()
        if new_ae:
            self.config.update_system(role, ae_title=new_ae)

async def main():
    """メイン関数"""
    print("Connectathon DICOM System Tester")
    print("================================")
    print("This tool tests DICOM connectivity for AM, IM, and OF systems")
    print()
    
    # 設定管理
    config = ConnectathonConfig()
    config_manager = InteractiveConfigManager(config)
    
    # 対話式設定
    config_manager.interactive_setup()
    
    # テスト実行
    tester = ConnectathonDICOMTester(config)
    
    print("\n=== Starting DICOM Tests ===")
    
    # 基本接続テスト
    print("\n1. Basic Connectivity Test")
    results = await tester.test_all_systems()
    
    print("\nTest Results:")
    for role, success in results.items():
        system = config.get_system(role)
        status = "PASS" if success else "FAIL"
        print(f"  {role} ({system.ae_title}): {status}")
    
    # 詳細ステータス表示
    print("\n2. Detailed System Status")
    status = await tester.get_system_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 監視モード（オプション）
    monitor = input("\nRun continuous monitoring? (y/n): ").strip().lower()
    if monitor == 'y':
        try:
            await tester.run_monitoring_cycle(interval=30, cycles=5)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
    
    print("\nTesting completed!")

if __name__ == "__main__":
    asyncio.run(main())