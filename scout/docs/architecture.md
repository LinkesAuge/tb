# TB Scout Architecture Overview

## Introduction

TB Scout is a Python application designed to automate interactions with the "Total Battle" game. It creates a transparent overlay on the game window to highlight detected elements and provides a GUI to control scanning and automation features. The application uses computer vision techniques to identify game elements and can perform automated actions based on detected patterns.

## System Architecture

TB Scout follows a modular architecture with clear separation of concerns. The application is structured around several core components that work together to provide the complete functionality.

### High-Level Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Main Window    │◄───►│  Signal Bus     │◄───►│  Error Handler  │
│  (GUI)          │     │                 │     │                 │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                       Core Components                           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │             │  │             │  │             │             │
│  │  Window     │  │  Capture    │  │  Template   │             │
│  │  Interface  │◄─┤  Manager    │◄─┤  Matcher    │             │
│  │             │  │             │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │             │  │             │  │             │             │
│  │  Overlay    │  │  Text OCR   │  │  Template   │             │
│  │             │  │             │  │  Search     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    Automation Components                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │             │  │             │  │             │             │
│  │ Automation  │  │  Sequence   │  │  Progress   │             │
│  │ Core        │◄─┤  Executor   │◄─┤  Tracker    │             │
│  │             │  │             │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │             │  │             │  │             │             │
│  │  Action     │  │  Action     │  │  Action     │             │
│  │  Handlers   │  │  Handlers   │  │  Handlers   │             │
│  │  (Basic)    │  │  (Flow)     │  │  (Advanced) │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Main Window (GUI)
The main user interface that provides access to all application features. It contains multiple tabs for different functionality areas and manages user interactions.

### Signal Bus
A central communication hub that allows components to communicate with each other without direct dependencies. It uses Qt's signal-slot mechanism to provide a publish-subscribe pattern.

### Error Handler
Centralizes error management across the application, providing consistent error reporting, logging, and user notifications.

### Window Interface
Provides an abstraction layer for window management, allowing the application to interact with the game window regardless of whether it's a browser or standalone version.

### Capture Manager
Handles screen and window capture operations, providing high-quality screenshots for analysis by other components.

### Template Matcher
Uses computer vision techniques to identify game elements by matching template images against screenshots.

### Template Search
Provides advanced search capabilities for finding game elements across the game world, using the Template Matcher as its core engine.

### Text OCR
Extracts text from game screenshots using optical character recognition (OCR) techniques.

### Overlay
Creates a transparent window on top of the game to visualize detected elements and provide visual feedback to the user.

## Automation Components

### Automation Core
The central component of the automation system, coordinating all automation activities and providing a high-level API for automation tasks.

### Sequence Executor
Executes sequences of automation actions, managing flow control, error handling, and progress tracking.

### Progress Tracker
Monitors and reports on the progress of automation sequences, providing feedback to the user.

### Action Handlers
Specialized components that implement different types of automation actions:
- **Basic Actions**: Simple game interactions like clicks and key presses
- **Flow Actions**: Control flow operations like loops and conditionals
- **Advanced Flow Actions**: Complex flow control like parallel execution
- **Data Actions**: Operations for data manipulation and storage
- **Visual Actions**: Actions related to visual recognition and response

## Configuration System

TB Scout uses a flexible configuration system that allows customization of various aspects of the application:

- **Settings Management**: Handled by the ConfigManager component
- **Default Settings**: Provided in default_settings.json
- **User Settings**: Stored in settings.json, overriding defaults
- **Runtime Configuration**: Can be modified through the Settings tab

## Error Handling and Logging

The application implements comprehensive error handling and logging:

- **Centralized Error Handling**: Through the ErrorHandler component
- **Structured Logging**: Using Python's logging module with custom formatters
- **Log Levels**: Different levels for development and production
- **Visual Feedback**: Error notifications in the UI

## Extension Points

TB Scout is designed to be extensible in several ways:

- **Template System**: New game elements can be added by creating new template images
- **Action Handlers**: New automation actions can be implemented by creating new handler classes
- **UI Components**: The tab-based UI allows for adding new functionality tabs

## Conclusion

TB Scout's architecture emphasizes modularity, separation of concerns, and extensibility. Each component has a clear responsibility and interfaces well with other parts of the system. This design allows for easier maintenance, testing, and future enhancements.