package com.example.androidtestapp

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class SwipeListAdapter(private val items: MutableList<String>) : RecyclerView.Adapter<SwipeListViewHolder>() {
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SwipeListViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_swipe, parent, false)
        return SwipeListViewHolder(view)
    }

    override fun onBindViewHolder(holder: SwipeListViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    fun replace(newItems: List<String>) {
        items.clear()
        items.addAll(newItems)
        notifyDataSetChanged()
    }

    fun removeAt(position: Int): String {
        val removed = items.removeAt(position)
        notifyItemRemoved(position)
        return removed
    }
}

class SwipeListViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
    private val textView: TextView = itemView.findViewById(R.id.swipe_item_text)

    fun bind(label: String) {
        textView.text = label
    }
}
