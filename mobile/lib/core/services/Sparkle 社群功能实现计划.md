Sparkle 社群功能实现计划                                        
                                                                 
 概述                                                            
                                                                 
 基于社群功能实现指南，实现三大核心模块：                        
 1. 好友系统 - 基于共同课程/考试匹配                             
 2. 学习小队 (Squad) - 长期目标社群                              
 3. 冲刺群 (Sprint) - 短期临时群组，带DDL倒计时                  
                                                                 
 与现有架构的适配                                                
                                                                 
 需要将指南中的代码适配到项目现有模式：                          
                                                                 
 | 指南方案       | 现有模式          | 适配方案                 
          |                                                      
 |----------------|-------------------|------------------------- 
 ---------|                                                      
 | Integer主键    | UUID主键          | 使用UUID，继承BaseModel  
          |                                                      
 | 标准SQLAlchemy | SoftDeleteMixin   |                          
 继承SoftDeleteMixin支持软删除    |                              
 | freezed模型    | json_serializable | 使用@JsonSerializable +  
 copyWith |                                                      
 | 独立API服务类  | Repository模式    | 创建CommunityRepository  
          |                                                      
                                                                 
 ---                                                             
 一、后端实现                                                    
                                                                 
 1.1 数据库模型                                                  
                                                                 
 文件: backend/app/models/community.py                           
                                                                 
 新增表:                                                         
 - friendships: 好友关系(user_id, friend_id, status,             
 initiated_by, match_reason)                                     
 - groups: 群组(name, type, focus_tags, deadline, sprint_goal,   
 ...)                                                            
 - group_members: 群成员(group_id, user_id, role,                
 flame_contribution, ...)                                        
 - group_messages: 群消息(group_id, sender_id, message_type,     
 content, content_data)                                          
 - group_tasks: 群任务(group_id, title, description, tags, ...)  
 - group_task_claims: 任务认领(group_task_id, user_id,           
 personal_task_id, ...)                                          
                                                                 
 关键适配:                                                       
 - 所有模型继承 BaseModel (带UUID和软删除)                       
 - 外键使用 GUID 类型                                            
 - 使用 server_default=func.now() 替代 default=func.now()        
                                                                 
 1.2 Pydantic Schemas                                            
                                                                 
 文件: backend/app/schemas/community.py                          
                                                                 
 - FriendRequest, FriendResponse, FriendshipInfo,                
 FriendRecommendation                                            
 - GroupCreate, GroupUpdate, GroupInfo, GroupListItem            
 - GroupMemberInfo, MemberRoleUpdate                             
 - MessageSend, MessageInfo                                      
 - GroupTaskCreate, GroupTaskInfo                                
 - CheckinRequest, CheckinResponse                               
 - FlameStatus, GroupFlameStatus                                 
                                                                 
 1.3 服务层                                                      
                                                                 
 文件: backend/app/services/community_service.py                 
                                                                 
 - FriendshipService: 好友请求/响应/推荐                         
 - GroupService: 群组CRUD/加入/退出/搜索                         
 - GroupMessageService: 消息发送/获取                            
 - CheckinService: 打卡逻辑与火苗计算                            
 - GroupTaskService: 群任务创建/认领/完成                        
                                                                 
 1.4 API路由                                                     
                                                                 
 文件: backend/app/api/v1/community.py                           
                                                                 
 前缀: /api/v1/community                                         
                                                                 
 好友:                                                           
 - POST /friends/request - 发送好友请求                          
 - POST /friends/respond - 响应好友请求                          
 - GET /friends - 获取好友列表                                   
 - GET /friends/pending - 待处理请求                             
 - GET /friends/recommendations - 好友推荐                       
                                                                 
 群组:                                                           
 - POST /groups - 创建群组                                       
 - GET /groups - 我的群组                                        
 - GET /groups/search - 搜索公开群组                             
 - GET /groups/{id} - 群组详情                                   
 - POST /groups/{id}/join - 加入                                 
 - POST /groups/{id}/leave - 退出                                
                                                                 
 消息:                                                           
 - GET /groups/{id}/messages - 获取消息                          
 - POST /groups/{id}/messages - 发送消息                         
                                                                 
 打卡:                                                           
 - POST /checkin - 群组打卡                                      
                                                                 
 群任务:                                                         
 - GET /groups/{id}/tasks - 任务列表                             
 - POST /groups/{id}/tasks - 创建任务                            
 - POST /tasks/{id}/claim - 认领任务                             
                                                                 
 火堆:                                                           
 - GET /groups/{id}/flame - 火堆状态                             
                                                                 
 1.5 LLM工具集成                                                 
                                                                 
 文件: backend/app/tools/community_tools.py                      
                                                                 
 - CreateSprintGroupTool: 创建冲刺群                             
 - InviteToGroupTool: 邀请好友                                   
 - ShareProgressTool: 分享进度                                   
 - GroupCheckinTool: 群组打卡                                    
                                                                 
 1.6 数据库迁移                                                  
                                                                 
 alembic revision --autogenerate -m "add_community_tables"       
 alembic upgrade head                                            
                                                                 
 ---                                                             
 二、前端实现                                                    
                                                                 
 2.1 数据模型                                                    
                                                                 
 文件: mobile/lib/data/models/community_model.dart               
                                                                 
 // 枚举                                                         
 enum GroupType { squad, sprint }                                
 enum GroupRole { owner, admin, member }                         
 enum MessageType { text, taskShare, progress, achievement,      
 checkin, system }                                               
 enum FriendshipStatus { pending, accepted, blocked }            
                                                                 
 // 模型类 (使用 @JsonSerializable)                              
 - UserBrief                                                     
 - FriendshipInfo, FriendRecommendation                          
 - GroupInfo, GroupListItem, GroupMemberInfo                     
 - MessageInfo                                                   
 - GroupTaskInfo                                                 
 - CheckinResponse                                               
 - FlameStatus, GroupFlameStatus                                 
                                                                 
 2.2 Repository                                                  
                                                                 
 文件: mobile/lib/data/repositories/community_repository.dart    
                                                                 
 class CommunityRepository {                                     
   // 好友                                                       
   Future<List<FriendshipInfo>> getFriends()                     
   Future<void> sendFriendRequest(String targetUserId, {String?  
 message})                                                       
   Future<void> respondToRequest(String friendshipId, bool       
 accept)                                                         
   Future<List<FriendRecommendation>>                            
 getFriendRecommendations({int limit})                           
                                                                 
   // 群组                                                       
   Future<GroupInfo> createGroup({...})                          
   Future<GroupInfo> getGroup(String groupId)                    
   Future<List<GroupListItem>> getMyGroups()                     
   Future<List<GroupListItem>> searchGroups({...})               
   Future<void> joinGroup(String groupId)                        
   Future<void> leaveGroup(String groupId)                       
                                                                 
   // 消息                                                       
   Future<List<MessageInfo>> getMessages(String groupId,         
 {String? beforeId, int limit})                                  
   Future<MessageInfo> sendMessage(String groupId, {...})        
                                                                 
   // 打卡                                                       
   Future<CheckinResponse> checkin(String groupId, {required int 
  todayDurationMinutes, String? message})                        
                                                                 
   // 群任务                                                     
   Future<List<GroupTaskInfo>> getGroupTasks(String groupId)     
   Future<void> claimTask(String taskId)                         
                                                                 
   // 火堆                                                       
   Future<GroupFlameStatus> getFlameStatus(String groupId)       
 }                                                               
                                                                 
 2.3 Riverpod Providers                                          
                                                                 
 文件: mobile/lib/presentation/providers/community_provider.dart 
                                                                 
 // 好友列表                                                     
 final friendsProvider = StateNotifierProvider<FriendsNotifier,  
 FriendsState>                                                   
                                                                 
 // 我的群组                                                     
 final myGroupsProvider =                                        
 StateNotifierProvider<MyGroupsNotifier, MyGroupsState>          
                                                                 
 // 群组详情 (Family)                                            
 final groupDetailProvider =                                     
 StateNotifierProvider.family<GroupDetailNotifier,               
 GroupDetailState, String>                                       
                                                                 
 // 群聊消息                                                     
 final groupChatProvider =                                       
 StateNotifierProvider.family<GroupChatNotifier, GroupChatState, 
  String>                                                        
                                                                 
 // 群组搜索                                                     
 final groupSearchProvider =                                     
 StateNotifierProvider<GroupSearchNotifier, GroupSearchState>    
                                                                 
 2.4 UI组件                                                      
                                                                 
 目录: mobile/lib/presentation/widgets/community/                
                                                                 
 - flame_avatar.dart          # 带火苗效果的头像                 
 - bonfire_animation.dart     # 火堆动画 (CustomPainter)         
 - message_bubble.dart        # 群消息气泡                       
 - checkin_card.dart          # 打卡卡片                         
 - progress_card.dart         # 进度分享卡片                     
 - achievement_card.dart      # 成就卡片                         
 - group_task_card.dart       # 群任务卡片                       
 - group_list_tile.dart       # 群组列表项                       
 - friend_list_tile.dart      # 好友列表项                       
                                                                 
 2.5 页面                                                        
                                                                 
 目录: mobile/lib/presentation/screens/community/                
                                                                 
 - friends_screen.dart         # 好友列表                        
 - friend_recommendations_screen.dart  # 好友推荐                
 - group_list_screen.dart      # 我的群组                        
 - group_search_screen.dart    # 搜索群组                        
 - group_detail_screen.dart    # 群组详情                        
 - group_chat_screen.dart      # 群聊界面                        
 - create_group_screen.dart    # 创建群组                        
 - group_tasks_screen.dart     # 群任务列表                      
 - group_members_screen.dart   # 群成员管理                      
                                                                 
 2.6 路由配置                                                    
                                                                 
 更新: mobile/lib/app/routes.dart                                
                                                                 
 // 添加社群相关路由                                             
 /community/friends                                              
 /community/friends/recommendations                              
 /community/groups                                               
 /community/groups/search                                        
 /community/groups/create                                        
 /community/groups/:id                                           
 /community/groups/:id/chat                                      
 /community/groups/:id/tasks                                     
 /community/groups/:id/members                                   
                                                                 
 ---                                                             
 三、实现顺序 (MVP优先) - 用户确认                               
                                                                 
 用户选择: MVP优先 + json_serializable                           
                                                                 
 Phase 1: 后端核心 (P0) - 群组 + 消息                            
                                                                 
 1. 创建 models/community.py - 群组、成员、消息模型              
 2. 创建数据库迁移并执行                                         
 3. 创建 schemas/community.py - 群组相关schemas                  
 4. 创建 services/community_service.py - GroupService,           
 MessageService                                                  
 5. 创建 api/v1/community.py - 群组和消息API                     
 6. 更新 api/v1/router.py - 注册路由                             
                                                                 
 Phase 2: 前端核心 (P0) - 群组 + 群聊                            
                                                                 
 7. 创建 data/models/community_model.dart -                      
 使用@JsonSerializable                                           
 8. 运行 flutter pub run build_runner build                      
 9. 创建 data/repositories/community_repository.dart             
 10. 创建 presentation/providers/community_provider.dart         
 11. 创建群组列表页面 group_list_screen.dart                     
 12. 创建群聊界面 group_chat_screen.dart                         
 13. 创建创建群组页面 create_group_screen.dart                   
 14. 创建群组详情页面 group_detail_screen.dart                   
 15. 更新路由配置                                                
                                                                 
 Phase 3: 打卡功能 (P1)                                          
                                                                 
 16. 后端: 添加打卡服务和API                                     
 17. 前端: 打卡UI组件和逻辑                                      
                                                                 
 Phase 4: 群任务功能 (P1)                                        
                                                                 
 18. 后端: 群任务模型、服务、API                                 
 19. 前端: 群任务页面和组件                                      
                                                                 
 Phase 5: 好友系统 (P1)                                          
                                                                 
 20. 后端: 好友模型、服务、API                                   
 21. 前端: 好友列表和推荐页面                                    
                                                                 
 Phase 6: 增强功能 (P2)                                          
                                                                 
 22. 火堆动画组件                                                
 23. LLM工具集成                                                 
 24. 消息模板组件（进度分享、成就等）                            
                                                                 
 ---                                                             
 四、关键文件清单                                                
                                                                 
 后端 (新增)                                                     
                                                                 
 - backend/app/models/community.py                               
 - backend/app/schemas/community.py                              
 - backend/app/services/community_service.py                     
 - backend/app/api/v1/community.py                               
 - backend/app/tools/community_tools.py                          
 - backend/alembic/versions/xxx_add_community_tables.py          
                                                                 
 后端 (修改)                                                     
                                                                 
 - backend/app/api/v1/router.py - 注册community路由              
 - backend/app/models/__init__.py - 导出新模型                   
 - backend/app/tools/registry.py - 注册新工具                    
                                                                 
 前端 (新增)                                                     
                                                                 
 - mobile/lib/data/models/community_model.dart                   
 - mobile/lib/data/models/community_model.g.dart (生成)          
 - mobile/lib/data/repositories/community_repository.dart        
 - mobile/lib/presentation/providers/community_provider.dart     
 - mobile/lib/presentation/screens/community/*.dart (9个页面)    
 - mobile/lib/presentation/widgets/community/*.dart (8个组件)    
                                                                 
 前端 (修改)                                                     
                                                                 
 - mobile/lib/app/routes.dart - 添加路由                         
 - mobile/lib/core/network/api_endpoints.dart - 添加端点         
                                                                 
 ---                                                             
 五、注意事项                                                    
                                                                 
 1. UUID vs Integer: 指南使用Integer                             
 ID，需要全部改为UUID以匹配现有模式                              
 2. 软删除: 所有新模型需继承SoftDeleteMixin                      
 3. 代码生成: Flutter模型修改后必须运行 build_runner             
 4. API端点: 统一使用 /api/v1/community 前缀                     
 5. 火苗计算: 打卡火苗公式: base(10) + streak_bonus(max 20) +    
 duration_bonus(max 30)                         