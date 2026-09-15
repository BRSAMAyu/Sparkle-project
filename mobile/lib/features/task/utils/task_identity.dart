final RegExp _uuidPattern = RegExp(
  r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
);

bool isServerTaskId(String id) => _uuidPattern.hasMatch(id);

bool isLocalOnlyTaskId(String id) => !isServerTaskId(id);
