# Building Generator v2.0

A powerful Python application for generating and managing building footprints for Falcon BMS simulation environments. This tool processes geospatial data from various sources and generates buildings compatible with Falcon BMS theaters.

## 🚀 Features

### Core Functionality

- **Geospatial Data Processing**: Import and process GeoJSON building footprint data
- **BMS Integration**: Direct injection of building data into Falcon BMS installations
- **Advanced Filtering**: Filter buildings by various criteria including size, type, and location
- **Multi-Source Support**: Compatible with Microsoft Building Footprints and Google Open Buildings
- **Statistical Analysis**: Generate detailed statistics about building distributions

### Advanced Features

- **Collision Detection**: Prevent overlapping buildings in generated layouts
- **Template System**: Customizable templates for different building types
- **Batch Processing**: Process multiple datasets efficiently
- **Backup Management**: Automatic backup of original BMS files
- **Real-time Preview**: 2D and 3D visualization of generated buildings

### Version 2.0 Highlights

- New FootPrints page with interactive map (tkintermapview) and AOI bbox overlay
- Microsoft download + optional division, Google CSV/tile ID handling with division
- Unified Extraction button with Microsoft/Google switch and extra fields option
- Standardized footprints paths under `root/footprints/...` with clear Google tiles source
- Robust error handling with suggestions and cancellable long operations

### Version 1.5 Enhancements

- **Modular Architecture**: Completely redesigned with component-based structure
- **Enhanced Settings Window**: Tabbed interface with comprehensive configuration options
- **BMS Injection Window**: Dedicated interface for BMS objective configuration
- **Improved Logging**: Configurable logging system with multiple output options
- **JSON Data Management**: Centralized JSON file handling with validation
- **Performance Optimizations**: Background processing and caching system

## 📋 Requirements

### System Requirements

- **OS**: Windows 10/11 (Primary), Linux (Experimental)
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space for installation and data

### Dependencies

```bash
pip install tkinter customtkinter tkintermapview numpy pandas geopandas matplotlib tqdm
pip install shapely rtree pathlib lxml pillow
```

## 🔧 Installation

1. **Download the latest release** from the releases section
2. **Extract** the archive to your desired location
3. **Install dependencies**:
   
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**:
   
   ```bash
   python MainGui.py
   ```

## 📖 Quick Start

### Basic Workflow

1. **Load CT File**: Select your Falcon BMS Campaign Theater XML file
2. **Import GeoData**: Load your building footprint GeoJSON file
3. **Configure Settings**: Set generation parameters and filters
4. **Generate Buildings**: Create building layouts with collision detection
5. **Export Results**: Save as GeoJSON or inject directly into BMS

### FootPrints (new) — Quick Path
1. Open FootPrints page
2. Enter AOI coordinates and click “Update BBox”
3. For Microsoft: type country, choose Divide (optional), Download
4. For Google: enter tile ID or Browse a CSV, Divide (optional)
5. In Saving: pick Microsoft/Google, set filename/folder, click “Extraction”

### First Time Setup

1. Open the application
2. Go to Settings → Load Preset to configure initial paths
3. Select your BMS installation directory
4. Load a sample GeoJSON file to test functionality

## 🎯 Key Improvements from v1.0 to v1.5

### Architecture Overhaul

- **Modular Design**: Separated functionality into components and utilities
- **Clean Separation**: UI, logic, and data handling are now properly separated
- **Extensible Framework**: Easy to add new features and data sources

### User Experience

- **Enhanced Settings**: Tabbed interface with better organization
- **BMS Integration**: Direct injection capabilities with template management
- **Improved Feedback**: Better error handling and user notifications
- **Processing Windows**: Long-running operations with progress indicators

### Technical Improvements

- **Performance**: Background processing and caching for large datasets
- **Reliability**: Comprehensive error handling and data validation
- **Maintainability**: Clean code structure with proper documentation
- **Logging**: Configurable logging system for debugging and monitoring

## 📁 Project Structure

```
Building Generator/
├── MainGui.py              # Main application entry point
├── building_extractor.py   # Core footprints algorithms (MS/Google extract & divide)
├── bms_injector.py         # BMS injection functionality
├── MainCode.py             # Core business logic
├── components/             # Modular components
│   ├── settings_window.py  # Enhanced settings interface
│   ├── bms_injection_window.py # BMS configuration window
│   ├── objective_cache.py  # Caching system
│   └── ...
├── utils/                  # Utility modules
│   ├── json_path_handler.py # JSON file management
│   ├── file_manager.py     # File operations
│   ├── logger.py          # Logging utilities
│   └── config.py          # Configuration management
├── data_components/        # Data and templates
│   ├── objective_templates.json
│   ├── ct_templates.json
│   └── ...
├── docs/                   # Documentation
├── Assets/                 # UI assets and icons
├── footprints/             # Standardized footprints root
│   ├── microsoft/
│   │   └── <country>/      # Divided chunks or <country>.geojson
│   └── google/
│       ├── tiles.geojson   # Required for Google division
│       └── <tile_id>/
│           └── <tile_id>_chunks/  # Divided Google chunks
└── Generated/             # Output directory
```

## 🎮 BMS Integration

The Building Generator provides seamless integration with Falcon BMS:

### Supported BMS Versions

- Falcon BMS 4.38+ 

### Integration Features

- **Direct Injection**: Generate buildings directly into BMS theaters
- **Objective Management**: Create and manage BMS objectives
- **Template System**: Customizable templates for different objective types
- **Backup System**: Automatic backup of original BMS files

## 🔧 Configuration

### Settings Files

- `config.json`: Main application configuration
- `data_components/objective_templates.json`: BMS objective templates
- `data_components/ct_templates.json`: Class Table templates
- `data_components/ValuesDic.json`: Value mappings for building types

### Key Configuration Options

- **Auto-Start**: Automatically load previous session
- **Logging**: Configure logging level and output
- **Backup**: Control backup creation and management
- **BMS Paths**: Set paths to BMS installation and data files

## 📊 Data Sources

### Supported Formats

- **GeoJSON**: Primary format for building footprint data
- **Microsoft Building Footprints**: Global building footprint dataset
- **Google Open Buildings**: Open source building data
- **QGIS**: Featuring extraction of Building data based on Opend Street Map (OSM)
- **OverPass-Turbo**: Easy and fast Web UI for extraction data based on OSM

### Data Processing

- **Filtering**: Filter by size, type, location, and custom criteria
- **Validation**: Automatic data validation and error correction
- **Transformation**: Convert between coordinate systems and projections
- **Optimization**: Spatial indexing for large datasets

## 🛠️ Development

### Getting Started

1. Clone the repository
2. Install development dependencies

### Contributing

- Follow the existing code style and structure
- Add tests for new functionality
- Update documentation for changes
- Submit pull requests with clear descriptions

## 📚 Documentation

- **[User Guide](docs/User Guide.pdf)**: Comprehensive usage instructions
- **[Changelog](CHANGELOG.md)**: Version history and changes
  

## 🐛 Troubleshooting

### Common Issues

- **BMS Path Not Found**: Ensure BMS installation path is correctly configured
- **GeoJSON Loading Error**: Verify file format and coordinate system
- **Memory Issues**: Reduce dataset size or enable data streaming
- **Permission Errors**: Run as administrator for BMS file modifications
- **Wrong Representation**: Showing extracted data from within the program may be wrong by undetected glitch. Features will anyway fitted correctly by their bonding box in BMS.

### Support

- Check the [User Guide](docs/User Guide.pdf) for detailed instructions
- Review log files in the `logs/` directory
- Report issues with detailed error messages and system information

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Falcon BMS Community for testing and feedback
- Microsoft Building Footprints team for global building data
- Google Open Buildings project for open source building data
- Python geospatial community for excellent tools and libraries

---

**Version**: 1.5.0  
**Last Updated**: June 2025  
**Compatibility**: Falcon BMS 4.35+, Python 3.8+ 