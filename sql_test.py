import re

rows = [
    {
        "course_name": "TA制程品質解析",
        "teaching_types": "試點1,試跑1",
        "teaching_scores": "91.64,94.05",
        "teaching_factory": "觀瀾,觀瀾"
    },
    {
        "course_name": "品質工具",
        "teaching_types": "試點3,試點4,正式交付1,正式交付2,正式交付5,正式交付6,正式交付10,正式交付18,正式交付19,正式交付21,正式交付22,正式交付25,正式交付31",
        "teaching_scores": "88.44,82.7,94,95.44,95.5,95.96,94.32,94.44,95.58,96.65,95.73,96.14,95.58",
        "teaching_factory": "觀瀾,觀瀾,綜保區,綜保區,綜保區,綜保區,加工區,加工區,加工區,蘭考,鶴壁,周口,蘭考"
    },
    {
        "course_name": "品質管理概論",
        "teaching_types": "正式交付3,正式交付9,正式交付10,正式交付12,正式交付17,正式交付25",
        "teaching_scores": "95.14,96.62,96.67,96.9,96.53,95.32",
        "teaching_factory": "綜保區,觀瀾,綜保區,綜保區,綜保區,綜保區"
    }
]

factory_codes = {
    '觀瀾': 'GL',
    '晉城': 'JC',
    '太原': 'TY',
    '綜保區': 'ZZK',
    '濟源': 'JY',
    '加工區': 'ZZC',
    '蘭考': 'LK',
    '龍華': 'LH',
    '鶴壁': 'HB',
    '周口': 'ZK'
}

# 第一步：为每个课程生成 new_teaching_types
for course in rows:
    teaching_types = course.get('teaching_types', '').split(',')
    teaching_factories = course.get('teaching_factory', '').split(',')
    
    new_teaching_types = []
    
    for i, teaching_type in enumerate(teaching_types):
        if i < len(teaching_factories):
            factory = teaching_factories[i]
            
            match = re.match(r'([^\d]+)(\d+)$', teaching_type.strip())
            if match:
                prefix = match.group(1)
                number = match.group(2)
            else:
                prefix = teaching_type.strip()
                number = ""
                
            factory_code = factory_codes.get(factory.strip(), factory.strip())
            new_teaching_type = f"{prefix}{factory_code}{number}" if number else f"{prefix}{factory_code}"
            new_teaching_types.append(new_teaching_type)
    
    course['new_teaching_types'] = new_teaching_types

# 第二步：找出所有课程中相同的 teaching_type 并合并显示
# 创建一个字典来存储每个 teaching_type 对应的工厂代码
teaching_type_factories = {}

# 收集所有 teaching_type 和对应的工厂代码
for course in rows:
    teaching_types = course.get('teaching_types', '').split(',')
    teaching_factories = course.get('teaching_factory', '').split(',')
    
    for i, teaching_type in enumerate(teaching_types):
        if i < len(teaching_factories):
            factory = teaching_factories[i].strip()
            factory_code = factory_codes.get(factory, factory)
            
            if teaching_type not in teaching_type_factories:
                teaching_type_factories[teaching_type] = set()
            
            teaching_type_factories[teaching_type].add(factory_code)

# 第三步：创建合并后的 teaching_type 映射
merged_teaching_types = {}
for teaching_type, factories in teaching_type_factories.items():
    match = re.match(r'([^\d]+)(\d+)$', teaching_type.strip())
    if match:
        prefix = match.group(1)
        number = match.group(2)
        
        if len(factories) == 1:
            # 只有一个工厂
            factory_code = list(factories)[0]
            merged_teaching_types[teaching_type] = f"{prefix}{factory_code}{number}"
        else:
            # 多个工厂，用 & 连接
            sorted_factories = sorted(list(factories))
            factories_str = '&'.join(sorted_factories)
            merged_teaching_types[teaching_type] = f"{prefix}{factories_str}{number}"
    else:
        # 没有数字的情况
        prefix = teaching_type.strip()
        if len(factories) == 1:
            factory_code = list(factories)[0]
            merged_teaching_types[teaching_type] = f"{prefix}{factory_code}"
        else:
            sorted_factories = sorted(list(factories))
            factories_str = '&'.join(sorted_factories)
            merged_teaching_types[teaching_type] = f"{prefix}{factories_str}"

# 第四步：更新每个课程的 new_teaching_types
for course in rows:
    teaching_types = course.get('teaching_types', '').split(',')
    merged_types = []
    
    for teaching_type in teaching_types:
        if teaching_type in merged_teaching_types:
            merged_types.append(merged_teaching_types[teaching_type])
        else:
            merged_types.append(teaching_type)  #  fallback
    
    course['merged_teaching_types'] = ','.join(merged_types)
print(rows[0]['merged_teaching_types'])
print(rows[1]['merged_teaching_types'])
print(rows[2]['merged_teaching_types'])

# # 打印结果
# for course in rows:
#     print(f"课程: {course['course_name']}")
#     print(f"原始 teaching_types: {course['teaching_types']}")
#     print(f"合并后的 teaching_types: {course['merged_teaching_types']}")
#     print("-" * 50)

# # 也可以查看合并映射关系
# print("\n合并映射关系:")
# for original, merged in merged_teaching_types.items():
#     print(f"{original} -> {merged}")