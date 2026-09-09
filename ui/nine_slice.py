import pygame

CORNER_SIZE = 3


def slice_image(source_surface, corner_size=CORNER_SIZE):
    w, h = source_surface.get_size()
    c = corner_size
    mid_w = w - 2 * c
    mid_h = h - 2 * c

    def crop(x, y, width, height):
        return source_surface.subsurface(pygame.Rect(x, y, width, height)).copy()

    return {
        "top_left":     crop(0, 0, c, c),
        "top":          crop(c, 0, mid_w, c),
        "top_right":    crop(w - c, 0, c, c),
        "left":         crop(0, c, c, mid_h),
        "center":       crop(c, c, mid_w, mid_h),
        "right":        crop(w - c, c, c, mid_h),
        "bottom_left":  crop(0, h - c, c, c),
        "bottom":       crop(c, h - c, mid_w, c),
        "bottom_right": crop(w - c, h - c, c, c),
    }


def render_nine_slice(pieces, target_width, target_height, corner_size=CORNER_SIZE, scale=1):
    
    display_corner = corner_size * scale
    result = pygame.Surface((target_width, target_height), pygame.SRCALPHA)

    inner_w = target_width - 2 * display_corner
    inner_h = target_height - 2 * display_corner

    def scaled(piece, w, h):
        return pygame.transform.scale(piece, (w, h))

    result.blit(scaled(pieces["top_left"], display_corner, display_corner), (0, 0))
    result.blit(scaled(pieces["top_right"], display_corner, display_corner), (target_width - display_corner, 0))
    result.blit(scaled(pieces["bottom_left"], display_corner, display_corner), (0, target_height - display_corner))
    result.blit(scaled(pieces["bottom_right"], display_corner, display_corner), (target_width - display_corner, target_height - display_corner))

    if inner_w > 0:
        result.blit(scaled(pieces["top"], inner_w, display_corner), (display_corner, 0))
        result.blit(scaled(pieces["bottom"], inner_w, display_corner), (display_corner, target_height - display_corner))

    if inner_h > 0:
        result.blit(scaled(pieces["left"], display_corner, inner_h), (0, display_corner))
        result.blit(scaled(pieces["right"], display_corner, inner_h), (target_width - display_corner, display_corner))

    if inner_w > 0 and inner_h > 0:
        result.blit(scaled(pieces["center"], inner_w, inner_h), (display_corner, display_corner))

    return result