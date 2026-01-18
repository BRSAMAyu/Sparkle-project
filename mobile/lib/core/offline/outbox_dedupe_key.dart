class OutboxDedupeKey {
  static String cognitiveCreate(String fragmentId) =>
      'cognitive:create:$fragmentId';

  static String knowledgeUpdate(String nodeId, String opId) =>
      'knowledge:update:$nodeId:$opId';
}
