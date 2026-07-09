// CircleMenu — React port of the prompt's component, mounted as an island
// inside the Vue WorkspaceView. Logic matches the prompt 1:1 (framer-motion
// AnimatePresence/useAnimationControls, pointOnCircle math, scaleTransition
// close animation). Two adaptations:
//   1. Tailwind utilities → regular CSS class names colocated in CircleMenu.css.
//      This project doesn't run Tailwind, so the original `bg-foreground`,
//      `rounded-full`, etc. would render as nothing without the swap.
//   2. Optional `onItemClick(key)` callback. The prompt uses <a href> for
//      navigation; in an SPA we need to fire Vue actions (logout, router push)
//      rather than navigate. When the callback is set, item clicks call it and
//      preventDefault. Without it, items behave as the prompt — anchors.
'use client'

import * as React from 'react'
import { useState } from 'react'
import { AnimatePresence, motion, useAnimationControls } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { cn } from '../../lib/utils'
import './CircleMenu.css'

const CONSTANTS = {
  itemSize: 48,
  containerSize: 250,
  openStagger: 0.02,
  closeStagger: 0.07,
}

const pointOnCircle = (i: number, n: number, r: number, cx = 0, cy = 0) => {
  const theta = (2 * Math.PI * i) / n - Math.PI / 2
  const x = cx + r * Math.cos(theta)
  const y = cy + r * Math.sin(theta)
  return { x, y }
}

// Linear "across" layout — items spread LEFT of the trigger in a horizontal row.
// Item 0 is closest to the trigger, item N is farthest. Negative x = leftward.
const pointInRow = (i: number, itemSize: number, gap: number) => ({
  x: -((i + 1) * (itemSize + gap)),
  y: 0,
})

// Vertical "down" layout — items stack DOWNWARD from the trigger.
// Useful when the trigger is anchored to a corner where horizontal expansion
// would clip off-screen (e.g. top-left corner of the home view).
const pointInColumn = (i: number, itemSize: number, gap: number) => ({
  x: 0,
  y: (i + 1) * (itemSize + gap),
})

// Diagonal "down-left" layout — items cascade DOWNWARD and toward the LEFT.
// Used for the in-strip trigger: it drops the icons below the tab strip (so they
// never fan across / cover the tabs) while opening leftward. Full vertical step,
// gentler horizontal step so the fan stays compact.
const pointInDiagonalDownLeft = (i: number, itemSize: number, gap: number) => ({
  x: -((i + 1) * (itemSize + gap) * 0.55),
  y: (i + 1) * (itemSize + gap),
})

type LayoutMode = 'circle' | 'across' | 'down' | 'down-left'

export interface CircleMenuItem {
  key: string
  label: string
  icon: React.ReactNode
  href?: string
}

interface MenuItemProps {
  item: CircleMenuItem
  index: number
  totalItems: number
  isOpen: boolean
  onItemClick?: (key: string) => void
  layout?: LayoutMode
  itemGap?: number
}

const MenuItem: React.FC<MenuItemProps> = ({
  item, index, totalItems, isOpen, onItemClick,
  layout = 'circle', itemGap = 10,
}) => {
  const { x, y } =
    layout === 'across' ? pointInRow(index, CONSTANTS.itemSize, itemGap)
    : layout === 'down' ? pointInColumn(index, CONSTANTS.itemSize, itemGap)
    : layout === 'down-left' ? pointInDiagonalDownLeft(index, CONSTANTS.itemSize, itemGap)
    : pointOnCircle(index, totalItems, CONSTANTS.containerSize / 2)
  const [hovering, setHovering] = useState(false)

  const handleClick = (e: React.MouseEvent) => {
    if (onItemClick) {
      e.preventDefault()
      onItemClick(item.key)
    }
  }

  return (
    <a href={item.href || '#'} className="cm-item-anchor" onClick={handleClick}>
      <motion.button
        animate={{ x: isOpen ? x : 0, y: isOpen ? y : 0 }}
        whileHover={{ scale: 1.1, transition: { duration: 0.1, delay: 0 } }}
        transition={{
          delay: isOpen ? index * CONSTANTS.openStagger : index * CONSTANTS.closeStagger,
          type: 'spring',
          stiffness: 300,
          damping: 30,
        }}
        style={{
          height: CONSTANTS.itemSize - 2,
          width: CONSTANTS.itemSize - 2,
        }}
        className="cm-item"
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        aria-label={item.label}
      >
        {item.icon}
        {hovering && isOpen && <span className="cm-label">{item.label}</span>}
      </motion.button>
    </a>
  )
}

interface MenuTriggerProps {
  setIsOpen: (isOpen: boolean) => void
  isOpen: boolean
  itemsLength: number
  closeAnimationCallback: () => void
  openIcon?: React.ReactNode
  closeIcon?: React.ReactNode
}

const MenuTrigger: React.FC<MenuTriggerProps> = ({
  setIsOpen,
  isOpen,
  itemsLength,
  closeAnimationCallback,
  openIcon,
  closeIcon,
}) => {
  const animate = useAnimationControls()
  const shakeAnimation = useAnimationControls()

  const scaleTransition = Array.from({ length: itemsLength - 1 })
    .map((_, index) => index + 1)
    .reduce((acc: number[], _, index) => {
      const increasedValue = index * 0.15
      acc.push(1 + increasedValue)
      return acc
    }, [] as number[])

  const closeAnimation = async () => {
    shakeAnimation.start({
      translateX: [0, 2, -2, 0, 2, -2, 0],
      transition: {
        duration: CONSTANTS.closeStagger,
        ease: 'linear',
        repeat: Infinity,
        repeatType: 'loop',
      },
    })
    for (let i = 0; i < scaleTransition.length; i++) {
      const target = Math.min(
        CONSTANTS.itemSize * scaleTransition[i],
        CONSTANTS.itemSize + CONSTANTS.itemSize / 2,
      )
      // Color-mix in plain CSS: from dark slate → softening toward background.
      const fg = '45, 37, 34' // RGB of our --dark-section
      const mix = Math.max(100 - i * 10, 40) / 100
      await animate.start({
        height: target,
        width: target,
        backgroundColor: `rgba(${fg}, ${mix})`,
        transition: { duration: CONSTANTS.closeStagger / 2, ease: 'linear' },
      })
      if (i !== scaleTransition.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, CONSTANTS.closeStagger * 1000))
      }
    }

    shakeAnimation.stop()
    shakeAnimation.start({ translateX: 0, transition: { duration: 0 } })

    animate.start({
      height: CONSTANTS.itemSize,
      width: CONSTANTS.itemSize,
      backgroundColor: 'rgb(45, 37, 34)',
      transition: { duration: 0.1, ease: 'backInOut' },
    })
  }

  return (
    <motion.div animate={shakeAnimation} className="cm-trigger-wrap">
      <motion.button
        animate={animate}
        style={{ height: CONSTANTS.itemSize, width: CONSTANTS.itemSize }}
        className={cn('cm-trigger', isOpen && 'cm-trigger--active')}
        onClick={() => {
          if (isOpen) {
            setIsOpen(false)
            closeAnimationCallback()
            closeAnimation()
          } else {
            setIsOpen(true)
          }
        }}
        aria-expanded={isOpen}
        aria-label="תפריט"
      >
        <AnimatePresence mode="popLayout">
          {isOpen ? (
            <motion.span
              key="menu-close"
              initial={{ opacity: 0, filter: 'blur(10px)' }}
              animate={{ opacity: 1, filter: 'blur(0px)' }}
              exit={{ opacity: 0, filter: 'blur(10px)' }}
              transition={{ duration: 0.2 }}
              style={{ display: 'inline-flex' }}
            >
              {closeIcon}
            </motion.span>
          ) : (
            <motion.span
              key="menu-open"
              initial={{ opacity: 0, filter: 'blur(10px)' }}
              animate={{ opacity: 1, filter: 'blur(0px)' }}
              exit={{ opacity: 0, filter: 'blur(10px)' }}
              transition={{ duration: 0.2 }}
              style={{ display: 'inline-flex' }}
            >
              {openIcon}
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>
    </motion.div>
  )
}

interface CircleMenuProps {
  items: CircleMenuItem[]
  openIcon?: React.ReactNode
  closeIcon?: React.ReactNode
  onItemClick?: (key: string) => void
  layout?: LayoutMode      // 'circle' (default — prompt) | 'across' (linear row to the left)
  itemGap?: number         // gap between items in 'across' mode
}

export const CircleMenu: React.FC<CircleMenuProps> = ({
  items,
  openIcon = <Menu size={18} color="#fff" />,
  closeIcon = <X size={18} color="#fff" />,
  onItemClick,
  layout = 'circle',
  itemGap = 10,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const animate = useAnimationControls()

  const closeAnimationCallback = async () => {
    await animate.start({
      rotate: -360,
      filter: 'blur(1px)',
      transition: {
        duration: CONSTANTS.closeStagger * (items.length + 2),
        ease: 'linear',
      },
    })
    await animate.start({
      rotate: 0,
      filter: 'blur(0px)',
      transition: { duration: 0 },
    })
  }

  // Wrap onItemClick to auto-close the menu after a click — same UX as a SPA expects.
  const handleItem = onItemClick
    ? (key: string) => {
        onItemClick(key)
        setIsOpen(false)
        closeAnimationCallback()
      }
    : undefined

  // Linear layouts ('across' / 'down') only need to host the trigger; items
  // extend outside via absolute positioning, so the mount-point footprint
  // stays small enough to dock inside a flex strip beside other buttons.
  const rootSize = layout === 'circle' ? CONSTANTS.containerSize : CONSTANTS.itemSize
  return (
    <div
      style={{ width: rootSize, height: rootSize }}
      className="cm-root"
    >
      <MenuTrigger
        setIsOpen={setIsOpen}
        isOpen={isOpen}
        itemsLength={items.length}
        closeAnimationCallback={closeAnimationCallback}
        openIcon={openIcon}
        closeIcon={closeIcon}
      />
      <motion.div animate={animate} className="cm-orbit">
        {items.map((item, index) => (
          <MenuItem
            key={`cm-${item.key}-${index}`}
            item={item}
            index={index}
            totalItems={items.length}
            isOpen={isOpen}
            onItemClick={handleItem}
            layout={layout}
            itemGap={itemGap}
          />
        ))}
      </motion.div>
    </div>
  )
}

export default CircleMenu
