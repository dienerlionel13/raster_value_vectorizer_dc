import os
import json

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'raster_value_vectorizer_dc_dialog_base.ui'))


class RasterValueVectorizerDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(RasterValueVectorizerDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        self.setupUi(self)
        
        # Connect signals
        self.mComboBoxMethod.currentIndexChanged.connect(self.mStackedWidget.setCurrentIndex)
        
        # Ranges buttons
        self.mButtonAddRow.clicked.connect(self.add_range_row)
        self.mButtonRemoveRow.clicked.connect(self.remove_range_row)
        self.mButtonSaveParams.clicked.connect(self.save_params)
        self.mButtonLoadParams.clicked.connect(self.load_params)
        
        # Unique value buttons
        self.mButtonAddUnique.clicked.connect(self.add_unique_value)
        self.mButtonRemoveUnique.clicked.connect(self.remove_unique_value)
        
        # Output
        self.mButtonBrowse.clicked.connect(self.select_output_file)
        self.mCheckBoxTemp.toggled.connect(self.toggle_output_file)
        
        # Populate raster layers
        self.populate_layers()

    def populate_layers(self):
        self.mMapLayerComboBox.clear()
        self.mMapLayerComboBoxMask.clear()
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsRasterLayer):
                self.mMapLayerComboBox.addItem(layer.name(), layer)
            elif isinstance(layer, QgsVectorLayer) and layer.geometryType() == 2: # 2 = Polygon
                self.mMapLayerComboBoxMask.addItem(layer.name(), layer)

    def toggle_output_file(self, checked):
        self.mLineEditOutput.setEnabled(not checked)
        self.mButtonBrowse.setEnabled(not checked)
        if checked:
            self.mLineEditOutput.clear()

    def add_range_row(self):
        row_count = self.mTableWidgetRanges.rowCount()
        self.mTableWidgetRanges.insertRow(row_count)

    def remove_range_row(self):
        current_row = self.mTableWidgetRanges.currentRow()
        if current_row >= 0:
            self.mTableWidgetRanges.removeRow(current_row)
        else:
            # Remove last if none selected
            row_count = self.mTableWidgetRanges.rowCount()
            if row_count > 0:
                self.mTableWidgetRanges.removeRow(row_count - 1)
                
    def add_unique_value(self):
        val = self.mSpinBoxUniqueToAdd.value()
        
        # Ask for label
        label, ok = QtWidgets.QInputDialog.getText(self, "Etiqueta", f"Ingrese etiqueta para el valor {val}:")
        if not ok:
            return # Cancelled
            
        if not label:
            label = "Valor Unico" # Default

        # Ask for tolerance/range
        tol, ok = QtWidgets.QInputDialog.getDouble(self, "Rango Adicional", 
            f"Ingrese rango adicional para {val} (0 para exacto).\nEjemplo: 0.01 para cubrir {val} hasta {val + 0.01}:", 
            value=0.0, decimals=6)
        if not ok:
            return # Cancelled
            
        # Check if already exists (check values stored in UserRole)
        exists = False
        for i in range(self.mListWidgetUnique.count()):
            item = self.mListWidgetUnique.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data['val'] == val:
                exists = True
                break
        
        if not exists:
            display_text = f"{val} ({label})"
            if tol > 0:
                display_text += f" [+{tol}]"
                
            item = QtWidgets.QListWidgetItem(display_text)
            # Store data as dict
            item.setData(Qt.UserRole, {'val': val, 'label': label, 'tol': tol})
            self.mListWidgetUnique.addItem(item)
            
    def remove_unique_value(self):
        current_row = self.mListWidgetUnique.currentRow()
        if current_row >= 0:
            self.mListWidgetUnique.takeItem(current_row)

    def save_params(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Guardar Parámetros", "", "JSON Files (*.json)")
        if filename:
            data = []
            rows = self.mTableWidgetRanges.rowCount()
            for r in range(rows):
                try:
                    min_val = self.mTableWidgetRanges.item(r, 0).text()
                    max_val = self.mTableWidgetRanges.item(r, 1).text()
                    cls_id = self.mTableWidgetRanges.item(r, 2).text() if self.mTableWidgetRanges.item(r, 2) else ""
                    data.append({"min": min_val, "max": max_val, "id": cls_id})
                except AttributeError:
                    continue
            
            try:
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=4)
                QtWidgets.QMessageBox.information(self, "Éxito", "Parámetros guardados correctamente.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo: {str(e)}")

    def load_params(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Cargar Parámetros", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.mTableWidgetRanges.setRowCount(0)
                for row_data in data:
                    row = self.mTableWidgetRanges.rowCount()
                    self.mTableWidgetRanges.insertRow(row)
                    self.mTableWidgetRanges.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row_data.get("min", ""))))
                    self.mTableWidgetRanges.setItem(row, 1, QtWidgets.QTableWidgetItem(str(row_data.get("max", ""))))
                    self.mTableWidgetRanges.setItem(row, 2, QtWidgets.QTableWidgetItem(str(row_data.get("id", ""))))
                
                QtWidgets.QMessageBox.information(self, "Éxito", "Parámetros cargados correctamente.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo cargar el archivo: {str(e)}")

    def select_output_file(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Select Output File", "", "Shapefile (*.shp);;GeoJSON (*.geojson)")
        if filename:
            self.mLineEditOutput.setText(filename)
