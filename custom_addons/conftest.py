import sys
from unittest.mock import Mock

# Dummy odoo mock for pytest collection
sys.modules["odoo"] = Mock()
sys.modules["odoo.http"] = Mock()
sys.modules["odoo.tests"] = Mock()
sys.modules["odoo.tests.common"] = Mock()
