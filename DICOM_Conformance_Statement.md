# DICOM適合性宣言書
## Image Store + Storage Commitment 統合テストクライアント

---

### 1. 製品概要

| 項目 | 詳細 |
|------|------|
| **製品名** | Image Store + Storage Commitment 統合テストクライアント |
| **バージョン** | 1.0.0 |
| **製造者** | Connect-a-thon 2025 |
| **実装クラスUID** | 1.2.392.200036.8120.101.9 |
| **実装バージョン名** | Monocube1.0.0.0 |
| **AE Title** | LTMONITOR |

### 2. 実装概要

本製品は、DICOMネットワーク通信における画像保存（C-STORE）とStorage Commitment機能を統合的にテストするクライアントアプリケーションです。以下の機能を提供します：

- **Secondary Capture Image Storage**: モノクロ画像の保存
- **True Color Secondary Capture**: RGB単一フレーム画像の保存
- **Multi-frame True Color Secondary Capture**: RGB複数フレーム画像の保存
- **Storage Commitment Push Model**: 画像保存確認要求と結果受信

---

## 3. ネットワークサービス

### 3.1 アプリケーションエンティティ仕様

| 項目 | 設定値 |
|------|--------|
| **AE Title** | LTMONITOR |
| **最大PDUサイズ** | 16,384 bytes |
| **ネットワークタイムアウト** | 10秒 |
| **ACSE タイムアウト** | 10秒 |
| **DIMSE タイムアウト** | 30秒 |

### 3.2 サポートするSOP Class

#### 3.2.1 Storage SOP Classes（SCU）

| SOP Class Name | SOP Class UID | 役割 | 実装状況 |
|----------------|---------------|------|---------|
| Secondary Capture Image Storage | 1.2.840.10008.5.1.4.1.1.7 | SCU | ✅ 完全対応 |
| Multi-frame True Color Secondary Capture Image Storage | 1.2.840.10008.5.1.4.1.1.7.4 | SCU | ⚠️ サーバー依存 |

**注意**: Multi-frame True Color Secondary Captureは一部のサーバーで処理エラーが発生するため、実用的にはSecondary Capture基盤でMulti-frame機能を実装しています。

#### 3.2.2 Non-Image SOP Classes

| SOP Class Name | SOP Class UID | 役割 |
|----------------|---------------|------|
| Storage Commitment Push Model | 1.2.840.10008.1.20.1 | SCU/SCP |

### 3.3 サポートするTransfer Syntax

| Transfer Syntax Name | Transfer Syntax UID |
|---------------------|-------------------|
| Implicit VR Little Endian | 1.2.840.10008.1.2 |
| Explicit VR Little Endian | 1.2.840.10008.1.2.1 |
| Explicit VR Big Endian | 1.2.840.10008.1.2.2 |
| JPEG Baseline (Process 1) | 1.2.840.10008.1.2.4.50 |
| JPEG Extended (Process 2 & 4) | 1.2.840.10008.1.2.4.70 |

---

## 4. 実装詳細

### 4.1 C-STORE Service（SCU）

#### 4.1.1 対応画像タイプ

##### Secondary Capture Image Storage
- **PhotometricInterpretation**: MONOCHROME2
- **SamplesPerPixel**: 1
- **BitsAllocated**: 8
- **BitsStored**: 8
- **PixelRepresentation**: 0
- **最小画像サイズ**: 16x16 pixels

##### True Color Secondary Capture
- **PhotometricInterpretation**: RGB
- **SamplesPerPixel**: 3
- **BitsAllocated**: 8
- **BitsStored**: 8
- **PixelRepresentation**: 0
- **PlanarConfiguration**: 0 (RGBRGBRGB...)
- **画像サイズ**: 32x32 pixels

##### Multi-frame True Color Secondary Capture
- **PhotometricInterpretation**: RGB
- **SamplesPerPixel**: 3
- **NumberOfFrames**: 2
- **BitsAllocated**: 8
- **BitsStored**: 8
- **PixelRepresentation**: 0
- **PlanarConfiguration**: 0
- **画像サイズ**: 32x32 pixels per frame

#### 4.1.2 必須DICOMモジュール

##### Patient Module
| 属性 | タグ | VR | 実装 | 設定例 |
|------|-----|----|----|--------|
| Patient Name | (0010,0010) | PN | 必須 | FUKUOKA^CHIHIRO, TANAKA^HANAKO, SUZUKI^ICHIRO |
| Patient ID | (0010,0020) | LO | 必須 | 1234567890（10桁固定） |
| Patient Birth Date | (0010,0030) | DA | 必須 | YYYYMMDD形式 |
| Patient Sex | (0010,0040) | CS | 必須 | M, F |

##### General Study Module
| 属性 | タグ | VR | 実装 |
|------|-----|----|----|
| Study Instance UID | (0020,000D) | UI | 必須 |
| Study Date | (0008,0020) | DA | 必須 |
| Study Time | (0008,0030) | TM | 必須 |
| Referring Physician Name | (0008,0090) | PN | オプション |
| Study ID | (0020,0010) | SH | 必須 |
| Accession Number | (0008,0050) | SH | 必須 |

##### General Series Module
| 属性 | タグ | VR | 実装 |
|------|-----|----|----|
| Series Instance UID | (0020,000E) | UI | 必須 |
| Series Number | (0020,0011) | IS | 必須 |
| Series Date | (0008,0021) | DA | 必須 |
| Series Time | (0008,0031) | TM | 必須 |
| Modality | (0008,0060) | CS | 必須（OT固定） |

##### Multi-frame Functional Groups Module（Multi-frameのみ）
| 属性 | タグ | VR | 実装 |
|------|-----|----|----|
| Shared Functional Groups Sequence | (5200,9229) | SQ | 必須 |
| Per-frame Functional Groups Sequence | (5200,9230) | SQ | 必須 |

### 4.2 Storage Commitment Service

#### 4.2.1 N-ACTION Request（SCU）
- **SOP Class UID**: 1.2.840.10008.1.20.1
- **SOP Instance UID**: 1.2.840.10008.1.20.1.1
- **Action Type ID**: 1

##### Storage Commitment Request Dataset
| 属性 | タグ | VR | 実装 |
|------|-----|----|----|
| Transaction UID | (0008,1195) | UI | 必須 |
| Referenced SOP Sequence | (0008,1199) | SQ | 必須 |
| > Referenced SOP Class UID | (0008,1150) | UI | 必須 |
| > Referenced SOP Instance UID | (0008,1155) | UI | 必須 |

#### 4.2.2 N-EVENT-REPORT（SCP）
- **ポート**: 11112
- **Event Type ID**: 1（成功）、2（失敗）

##### 受信可能な結果情報
| Event Type | 説明 | 対応 |
|------------|------|------|
| 1 | Storage Commitment Result - Success | ✓ |
| 2 | Storage Commitment Result - Failure | ✓ |

---

## 5. 設定情報

### 5.1 ネットワーク設定

| 項目 | 設定値 | 備考 |
|------|--------|------|
| **クライアントAE Title** | LTMONITOR | 固定 |
| **接続先IP** | 127.0.0.1 | ローカルホスト |
| **接続先ポート** | 11113 | IM Server |
| **Storage Commitment受信ポート** | 11112 | 固定 |

### 5.2 実装制限事項

#### 5.2.1 SOP Class制限
- **Multi-frame True Color Secondary Capture**: SOP Class UID `1.2.840.10008.5.1.4.1.1.7.4` は技術的にはサポートしているが、一部のIMサーバーで実装上の制約により接続が強制終了される
- **実用実装**: Multi-frame機能はSecondary Capture (`1.2.840.10008.5.1.4.1.1.7`) を基盤として実装し、完全な互換性を確保
- **JPEG圧縮**: サポートするが、無圧縮Transfer Syntaxを推奨

#### 5.2.2 タイムアウト設定
- **Storage Commitment結果受信**: 30秒
- **DIMSE操作**: 30秒
- **ネットワーク接続**: 10秒
- **ACSE協会確立**: 10秒

#### 5.2.3 互換性に関する注意事項
- **IMサーバー対応**:
  - ✅ Secondary Capture基盤のMulti-frame: 完全動作
  - ⚠️ Multi-frame True Color Secondary Capture: アソシエーション成功、データ処理でエラー
  - ✅ Storage Commitment: 完全動作（Request送信、結果受信）

---

## 6. セキュリティプロファイル

本実装はDICOMセキュリティプロファイルには対応していません。ネットワーク通信は平文で行われます。

---

## 7. 適合性テスト結果

### 7.1 テスト環境
- **OS**: Windows 11
- **Python**: 3.10.11
- **pynetdicom**: 最新版
- **接続先**: IMサーバー（ポート11113）

### 7.2 テスト結果

| テストケース | SOP Class UID | 結果 | 詳細 |
|------------|--------------|------|------|
| Secondary Capture C-STORE | 1.2.840.10008.5.1.4.1.1.7 | ✅ 成功 | 16x16 Monochrome画像 |
| True Color Secondary Capture C-STORE | 1.2.840.10008.5.1.4.1.1.7 | ✅ 成功 | 32x32 RGB単一フレーム |
| Multi-frame True Color C-STORE（SC基盤） | 1.2.840.10008.5.1.4.1.1.7 | ✅ 成功 | 32x32 RGB 2フレーム |
| Multi-frame True Color C-STORE（専用） | 1.2.840.10008.5.1.4.1.1.7.4 | ❌ 失敗 | アソシエーション成功、データ送信でConnectionReset |
| Storage Commitment Request | 1.2.840.10008.1.20.1 | ✅ 成功 | N-ACTION送信、Status 0x0000 |
| Storage Commitment Result受信 | 1.2.840.10008.1.20.1 | ✅ 成功 | N-EVENT-REPORT受信、Event Type ID = 1 |

### 7.3 エラー解析

#### Multi-frame True Color Secondary Capture (1.2.840.10008.5.1.4.1.1.7.4)
- **問題**: IMサーバーでのConnectionResetError
- **原因**: サーバー側でのDICOMデータ処理エラー
- **解決策**: Secondary Capture基盤でのMulti-frame実装を採用

---

## 8. 追加情報

### 8.1 実装上の注意点
- Multi-frame画像では最小限のFunctional Groups Moduleを実装し、サーバー互換性を重視
- Storage Commitment結果の受信はイベント駆動で実装
- エラーハンドリングとロギングを充実させ、デバッグを容易化

### 8.2 今後の拡張計画
- DICOM TLS通信のサポート
- より多くのImage SOP Classのサポート
- 圧縮Transfer Syntaxの最適化

---

**文書バージョン**: 1.0
**作成日**: 2025年9月18日
**最終更新**: 2025年9月18日