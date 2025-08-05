import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Setup required for PyQt tests: tells pytest this is a PyQt app
pytest.register_assert_rewrite("pytest_qt.asserts")

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QSettings, QDateTime, Qt

# --- Class to be tested ---
# It's good practice to place the file to be tested in a known location
# or ensure the python path is set up correctly.
# For this example, we assume `main.py` is in the same directory.
from main import Home, ProjectItemWidget

# Mock dependencies that are not part of the Home window's direct logic
# This prevents other windows from opening or functions from accessing the filesystem
MOCK_UTILS = "main.app.utils"
MOCK_MAIN_WINDOW = "main.app.main_window.MainWindow"

@pytest.fixture
def app(qtbot):
    """
    A pytest fixture to create the main application and Home window for testing.
    It uses mocking to isolate the Home window from its dependencies.
    """
    # Clear QSettings before each test to ensure a clean state
    QSettings("YourCompany", "MangaOCRTool").clear()

    # Patch external functions and classes to prevent them from actually running.
    # We just want to test if our Home window *calls* them correctly.
    with patch(f"{MOCK_UTILS}.new_project") as mock_new, \
         patch(f"{MOCK_UTILS}.open_project") as mock_open, \
         patch(f"{MOCK_UTILS}.import_from_wfwf") as mock_import, \
         patch(MOCK_MAIN_WINDOW, MagicMock()) as mock_mw:

        # Create the Home window instance
        window = Home()
        qtbot.addWidget(window) # Register the window with qtbot for interaction
        
        # Attach mocks to the window instance so we can access them in tests
        window.mock_new = mock_new
        window.mock_open = mock_open
        window.mock_import = mock_import
        window.mock_mw = mock_mw

        yield window # Provide the window to the test function

    # Cleanup after the test runs
    window.close()
    QSettings("YourCompany", "MangaOCRTool").clear()


# --- Test Cases ---

def test_home_window_initialization(app):
    """Test if the main window initializes with all expected widgets."""
    assert app.windowTitle() == "" # Title is in the custom bar now
    assert app.btn_new.text() == "New Project"
    assert app.btn_open.text() == "Open Project"
    assert app.btn_import.text() == "Import from WFWF"
    assert app.recent_label.text() == "Recent Projects"
    assert app.projects_list is not None
    # Check that initially, the project list is empty (only has a stretch item)
    assert app.projects_list.projects_layout.count() == 1

def test_button_clicks(app, qtbot):
    """Test if clicking the main action buttons calls the correct functions."""
    # Simulate clicking the "New Project" button
    qtbot.mouseClick(app.btn_new, Qt.LeftButton)
    app.mock_new.assert_called_once_with(app)

    # Simulate clicking the "Open Project" button
    qtbot.mouseClick(app.btn_open, Qt.LeftButton)
    app.mock_open.assert_called_once_with(app)

    # Simulate clicking the "Import from WFWF" button
    qtbot.mouseClick(app.btn_import, Qt.LeftButton)
    app.mock_import.assert_called_once_with(app)

def test_recent_projects_loading(app, qtbot):
    """Test if the window correctly loads and displays recent projects from QSettings."""
    # Manually set up QSettings to simulate a previous session
    settings = QSettings("YourCompany", "MangaOCRTool")
    fake_path = "/fake/project/proj1.mmtl"
    # To test loading, the file must "exist" for the mock
    with patch("os.path.exists", return_value=True):
        settings.setValue("recent_projects", [fake_path])
        
        # Set a specific timestamp
        timestamp = QDateTime.currentDateTime().addDays(-2).toString(Qt.ISODate)
        settings.setValue("recent_timestamps", {fake_path: timestamp})
        
        # Reload the projects in the app
        app.load_recent_projects()

        # Check if the project is now displayed in the list
        # We expect one project item + the stretch item
        assert app.projects_list.projects_layout.count() == 2 
        item = app.projects_list.projects_layout.itemAt(0).widget()
        assert isinstance(item, ProjectItemWidget)
        assert item.name_label.text() == "proj1.mmtl"
        assert item.last_opened_label.text() == "2 days ago"
        assert item.path == fake_path

def test_double_click_project_item(app, qtbot):
    """Test if double-clicking a project in the list launches the application."""
    fake_path = "/fake/project/double_click.mmtl"
    with patch("os.path.exists", return_value=True):
        # Add a project to the list
        item = app.projects_list.add_project("double_click.mmtl", fake_path, "Just now")
        app.projects_list.update() # Ensure UI is updated

        # Mock the launch function to check if it's called
        with patch.object(app, 'launch_main_app') as mock_launch:
            # Simulate a double-click on the project item widget
            qtbot.mouseDClick(item, Qt.LeftButton)
            
            # Assert that the launch function was called with the correct path
            mock_launch.assert_called_once_with(fake_path)

def test_launch_main_app_success(app, qtbot):
    """Test the successful project loading sequence."""
    fake_path = "/fake/project/success.mmtl"
    
    # Use patch to control the ProjectLoaderThread
    with patch("main.ProjectLoaderThread") as MockThread:
        # We need to manually control the thread's signals
        mock_thread_instance = MagicMock()
        # Make the thread emit the 'finished' signal when start() is called
        def start_and_emit():
            mock_thread_instance.finished.emit(fake_path, "/tmp/faketempdir")
        
        mock_thread_instance.start.side_effect = start_and_emit
        MockThread.return_value = mock_thread_instance

        # Call the function that starts the process
        app.launch_main_app(fake_path)

        # Check that the loading dialog is shown
        assert app.loading_dialog.isVisible()
        
        # Wait until the main window's 'process_mmtl' method is called
        def check_main_window_called():
            assert app.mock_mw.return_value.process_mmtl.called
        
        qtbot.waitUntil(check_main_window_called)

        # Verify the correct methods were called
        app.mock_mw.return_value.process_mmtl.assert_called_once_with(fake_path, "/tmp/faketempdir")
        app.mock_mw.return_value.show.assert_called_once()
        
        # Check that the loading dialog was closed
        assert not app.loading_dialog.isVisible()

def test_launch_main_app_error(app, qtbot):
    """Test the project loading sequence when an error occurs."""
    fake_path = "/fake/project/error.mmtl"
    error_message = "Invalid .mmtl file"

    # Mock QMessageBox to check if it's shown, without actually showing it
    with patch("main.QMessageBox.critical") as mock_msgbox, \
         patch("main.ProjectLoaderThread") as MockThread:
        
        mock_thread_instance = MagicMock()
        # Make the thread emit the 'error' signal
        def start_and_emit_error():
            mock_thread_instance.error.emit(error_message)

        mock_thread_instance.start.side_effect = start_and_emit_error
        MockThread.return_value = mock_thread_instance

        # Call the function
        app.launch_main_app(fake_path)

        # Wait until the message box is called
        qtbot.waitUntil(lambda: mock_msgbox.called)

        # Assert that the critical error message box was shown with the correct text
        mock_msgbox.assert_called_once()
        # Check the arguments passed to QMessageBox.critical
        args, _ = mock_msgbox.call_args
        assert args[1] == "Error"
        assert error_message in args[2]

        # Assert the loading dialog was closed
        assert not app.loading_dialog.isVisible()

@patch("main.QApplication") # Mock QApplication so it doesn't run
@patch("main.Home")
@patch("os.path.exists", return_value=True)
def test_main_script_with_valid_arg(mock_home, mock_exists, mock_app):
    """Test if main script launches app directly with valid command-line arg."""
    # Set command line arguments
    test_argv = ["main.py", "project.mmtl"]
    with patch.object(sys, 'argv', test_argv):
        # This is complex to test fully, so we check the intended logic:
        # Does it instantiate Home and call launch_main_app, but NOT show()?
        # We need a way to run the `if __name__ == "__main__"` block
        # A simple import doesn't run it, so we can extract the logic or exec it.
        # For simplicity, we'll test the core logic path.
        
        # Simulate the entry point logic
        window_instance = mock_home.return_value
        
        # The script would call launch_main_app
        # This test conceptually verifies the if/else block in __main__
        # In a real scenario, you would structure the __main__ block to be more testable,
        # e.g., by putting the logic in a function.
        
        # The core assertion is: if project_to_open is set, launch_main_app is called.
        # This requires refactoring the main block slightly to be testable.
        # Let's assume a conceptual `main_entry(argv)` function exists.
        
        # Based on the current structure, let's test the side effects.
        # The script creates a Home instance.
        from main import main # We need to import the module to re-evaluate it
        assert window_instance.launch_main_app.called
        assert not window_instance.show.called